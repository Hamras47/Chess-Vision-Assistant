$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

foreach ($target in @("build", "dist")) {
    $resolvedTarget = [IO.Path]::GetFullPath((Join-Path $projectRoot $target))
    if ([IO.Path]::GetDirectoryName($resolvedTarget) -ne [IO.Path]::GetFullPath($projectRoot)) { throw 'Unsafe build directory.' }
    if (Test-Path -LiteralPath $resolvedTarget) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}

python -m PyInstaller --clean --noconfirm ChessVision.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$executable = Join-Path $projectRoot "dist\ChessVision\ChessVision.exe"
if (-not (Test-Path -LiteralPath $executable)) { throw "Build completed without ChessVision.exe." }
Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_NOTICES.md") -Destination (Split-Path $executable) -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "docs\LICENSING.md") -Destination (Join-Path (Split-Path $executable) "LICENSING.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination (Split-Path $executable) -Force
python scripts/collect_licenses.py (Join-Path (Split-Path $executable) "licenses")
if ($LASTEXITCODE -ne 0) { throw "Dependency license collection failed." }
Write-Host "Built Chess Vision: $executable"
