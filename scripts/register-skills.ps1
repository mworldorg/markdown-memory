# register-skills.ps1
# Creates NTFS junctions from louise-skills/skills/<name>/ to ~/.claude/skills/<name>/
# Also sets MM_REPO_ROOT user env var so mm-* skills find config portably.
# Run after adding/removing a skill folder, or after `git pull`.
# Idempotent: skips if junction already correct, recreates if wrong target.

$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$SourceDir  = Join-Path $RepoRoot "skills"
$TargetRoot = Join-Path $env:USERPROFILE ".claude\skills"

if (-not (Test-Path $SourceDir))  { throw "Source dir not found: $SourceDir" }
if (-not (Test-Path $TargetRoot)) { throw "Target dir not found: $TargetRoot (Claude Code not installed?)" }

Write-Host "Repo:   $RepoRoot"
Write-Host "Source: $SourceDir"
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

$skills = Get-ChildItem -Directory $SourceDir
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
if ($errors -gt 0) { exit 1 }
