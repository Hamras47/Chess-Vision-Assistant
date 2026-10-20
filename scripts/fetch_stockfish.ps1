# Downloads the official Stockfish Windows build into engine\stockfish.exe so
# the app (source checkout or PyInstaller build) finds it without Settings.
param([string]$Tag = "sf_19")
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$engineDir = Join-Path $projectRoot "engine"
$asset = "stockfish-windows-x86-64-universal.zip"
$url = "https://github.com/official-stockfish/Stockfish/releases/download/$Tag/$asset"
$work = Join-Path ([IO.Path]::GetTempPath()) ("stockfish-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force $work, $engineDir | Out-Null
try {
    $zip = Join-Path $work $asset
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $work "x")
    $exe = Get-ChildItem (Join-Path $work "x") -Recurse -Filter "stockfish*.exe" | Select-Object -First 1
    if (-not $exe) { throw "No stockfish executable in $asset." }
    Copy-Item -LiteralPath $exe.FullName -Destination (Join-Path $engineDir "stockfish.exe") -Force
    $copying = Get-ChildItem (Join-Path $work "x") -Recurse -Filter "Copying.txt" | Select-Object -First 1
    if ($copying) { Copy-Item -LiteralPath $copying.FullName -Destination (Join-Path $engineDir "Stockfish-COPYING.txt") -Force }
    Write-Host "Stockfish $Tag installed: $(Join-Path $engineDir 'stockfish.exe')"
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
