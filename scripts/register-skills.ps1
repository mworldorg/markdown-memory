# register-skills.ps1
# Creates NTFS junctions from markdown-memory/skills/<name>/ and vendor/<name>/ to ~/.claude/skills/<name>/
# Also sets MM_REPO_ROOT user env var so mm-* skills find config portably.
# Run after adding/removing a skill folder, or after `git pull`.
# Idempotent: skips if junction already correct, recreates if wrong target.

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$SourceDir  = Join-Path $RepoRoot "skills"
$VendorDir  = Join-Path $RepoRoot "vendor"
$TargetRoot = Join-Path $env:USERPROFILE ".claude\skills"

if (-not (Test-Path $SourceDir))  { throw "Source dir not found: $SourceDir" }
if (-not (Test-Path $TargetRoot)) { throw "Target dir not found: $TargetRoot (Claude Code not installed?)" }

Write-Host "Repo:   $RepoRoot"
Write-Host "Source: $SourceDir"
if (Test-Path $VendorDir) { Write-Host "Vendor: $VendorDir (external skills)" }
Write-Host "Target: $TargetRoot"
Write-Host ""

# --- MM_REPO_ROOT env var (User scope, persistent across sessions) ---
$existingEnv = [Environment]::GetEnvironmentVariable("MM_REPO_ROOT", "User")
if ($existingEnv -ieq $RepoRoot) {
    Write-Host "[env]  MM_REPO_ROOT already set to this repo" -ForegroundColor DarkGray
} elseif ($existingEnv) {
    Write-Host "[env]  MM_REPO_ROOT was set to: $existingEnv" -ForegroundColor Yellow
    Write-Host "[env]  Updating to: $RepoRoot" -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("MM_REPO_ROOT", $RepoRoot, "User")
    $env:MM_REPO_ROOT = $RepoRoot
} else {
    [Environment]::SetEnvironmentVariable("MM_REPO_ROOT", $RepoRoot, "User")
    $env:MM_REPO_ROOT = $RepoRoot
    Write-Host "[env]  Set MM_REPO_ROOT = $RepoRoot (User scope)" -ForegroundColor Green
}
Write-Host ""

# --- Раскатка секций в ~/.claude/CLAUDE.md (по маркерам, чужое не трогаем) ---
# Источник: templates/claude-md/*.md, id секции = имя файла без .md.
# Логика обязана совпадать с register-skills.py — расхождение станет источником багов.
$TplDir    = Join-Path $RepoRoot "templates\claude-md"
$ClaudeMd  = Join-Path $env:USERPROFILE ".claude\CLAUDE.md"
$secAdded = 0; $secUpdated = 0; $secSkipped = 0; $secChanged = 0; $secErrors = 0

function Get-Sha8([string]$text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($text))
    return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "").Substring(0, 8)
}

if (Test-Path $TplDir) {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    foreach ($tpl in @(Get-ChildItem -File -Filter *.md $TplDir)) {
        $id  = [IO.Path]::GetFileNameWithoutExtension($tpl.Name)
        $raw = ([IO.File]::ReadAllText($tpl.FullName)) -replace "`r`n", "`n"
        $raw = $raw.TrimEnd()
        $sha = Get-Sha8 $raw

        $existed = Test-Path $ClaudeMd
        $text    = if ($existed) { [IO.File]::ReadAllText($ClaudeMd) } else { "" }
        $eol     = if ($text -match "`r`n") { "`r`n" } else { "`n" }

        $begin = "<!-- mm:begin $id sha=$sha -->"
        $end   = "<!-- mm:end $id -->"
        $block = $begin + $eol + ($raw -replace "`n", $eol) + $eol + $end

        # Осиротевший маркер: дописать вторую копию тихо хуже, чем отказаться —
        # Claude Code читает этот файл при каждом запуске.
        $hasBegin = [regex]::IsMatch($text, "<!-- mm:begin " + [regex]::Escape($id) + "(?: sha=[0-9a-f]+)? -->")
        $hasEnd   = [regex]::IsMatch($text, "<!-- mm:end " + [regex]::Escape($id) + " -->")
        if ($hasBegin -ne $hasEnd) {
            $which = if ($hasBegin) { "mm:begin without matching mm:end" } else { "mm:end without matching mm:begin" }
            Write-Host "  [error] section $id -> $which" -ForegroundColor Red
            Write-Host "          file: $ClaudeMd" -ForegroundColor Red
            Write-Host "          left unchanged; fix the markers by hand, then re-run" -ForegroundColor Red
            $secErrors++
            continue
        }

        $rx = [regex]("(?s)<!-- mm:begin " + [regex]::Escape($id) + "(?: sha=([0-9a-f]+))? -->(.*?)<!-- mm:end " + [regex]::Escape($id) + " -->")
        $m  = $rx.Match($text)

        if ($m.Success) {
            $inner = ($m.Groups[2].Value -replace "`r`n", "`n").Trim()
            if ($inner -eq $raw) {
                Write-Host "  [skip] section $id -> up to date" -ForegroundColor DarkGray
                $secSkipped++
                continue
            }
            if ($m.Groups[1].Value -ne (Get-Sha8 $inner)) {
                $bak = "$ClaudeMd.bak-" + (Get-Date -Format "yyyyMMdd-HHmmss")
                Copy-Item $ClaudeMd $bak
                Write-Host "  [changed] section $id -> block was hand-edited, it will be overwritten" -ForegroundColor Yellow
                Write-Host "            backup: $bak" -ForegroundColor Yellow
                $secChanged++
            } else {
                Write-Host "  [update] section $id -> template changed" -ForegroundColor Green
                $secUpdated++
            }
            $text = $text.Substring(0, $m.Index) + $block + $text.Substring($m.Index + $m.Length)
        } else {
            if ($text -and -not $text.EndsWith($eol)) { $text += $eol }
            $text = $text + $eol + $block + $eol
            Write-Host "  [ok]   section $id -> added" -ForegroundColor Green
            $secAdded++
        }
        [IO.File]::WriteAllText($ClaudeMd, $text, $utf8NoBom)
    }
    Write-Host ""
}

$skills = @(Get-ChildItem -Directory $SourceDir)
if (Test-Path $VendorDir) { $skills += Get-ChildItem -Directory $VendorDir }
$created = 0; $skipped = 0; $relinked = 0; $errors = 0

foreach ($skill in $skills) {
    $name       = $skill.Name
    $sourcePath = $skill.FullName
    $targetPath = Join-Path $TargetRoot $name

    if (Test-Path $targetPath) {
        # Check if existing path is a junction pointing where we want
        $item = Get-Item $targetPath -Force
        $isReparse = ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0

        if ($isReparse) {
            # Read the junction target
            $existingTarget = (Get-Item $targetPath).Target
            if ($existingTarget -and ($existingTarget.TrimEnd('\') -ieq $sourcePath.TrimEnd('\'))) {
                Write-Host "  [skip] $name -> already linked correctly" -ForegroundColor DarkGray
                $skipped++
                continue
            } else {
                Write-Host "  [relink] $name -> wrong target ($existingTarget), recreating" -ForegroundColor Yellow
                cmd /c rmdir "`"$targetPath`""
                $relinked++
            }
        } else {
            Write-Host "  [error] $name -> $targetPath exists and is NOT a junction. Manual intervention needed." -ForegroundColor Red
            $errors++
            continue
        }
    } else {
        $created++
    }

    # Create junction (cmd mklink /J — works without admin)
    $output = cmd /c mklink /J "`"$targetPath`"" "`"$sourcePath`"" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [ok]   $name" -ForegroundColor Green
    } else {
        Write-Host "  [fail] $name -> $output" -ForegroundColor Red
        $errors++
    }
}

Write-Host ""
Write-Host "Summary: created=$created relinked=$relinked skipped=$skipped errors=$errors"
Write-Host "Sections: added=$secAdded updated=$secUpdated skipped=$secSkipped hand-edited=$secChanged errors=$secErrors"
if ($errors -gt 0 -or $secErrors -gt 0) { exit 1 }
