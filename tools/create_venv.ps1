# filepath: .\tools\create_venv.ps1
param(
    [string]$Root = ".."
)
$venvPath = Join-Path $Root ".venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}
$activate = Join-Path $venvPath "Scripts\Activate.ps1"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
& $activate
python -m pip install --upgrade pip
if (Test-Path (Join-Path $Root "requirements.txt")) {
    python -m pip install -r (Join-Path $Root "requirements.txt")
}
if (Test-Path (Join-Path $Root "requirements-dev.txt")) {
    python -m pip install -r (Join-Path $Root "requirements-dev.txt")
}
# instalar pre-commit se disponível
python -m pip install pre-commit -q
pre-commit install || Write-Host "pre-commit install falhou (talvez não haja hooks configurados ainda)."
