$RepoRoot = Split-Path -Parent $PSScriptRoot

$env:JAVA_HOME = Join-Path $RepoRoot ".conda-jdk17\Library"
$env:PYTERRIER_HOME = Join-Path $RepoRoot ".cache\pyterrier"
$env:IR_DATASETS_HOME = Join-Path $RepoRoot ".cache\ir_datasets"
$env:VIRTUAL_ENV = Join-Path $RepoRoot ".venv"
$env:Path = "$env:VIRTUAL_ENV\Scripts;$env:JAVA_HOME\bin;$env:Path"

Write-Host "LongEval environment activated."
Write-Host "VIRTUAL_ENV=$env:VIRTUAL_ENV"
Write-Host "JAVA_HOME=$env:JAVA_HOME"
Write-Host "PYTERRIER_HOME=$env:PYTERRIER_HOME"
Write-Host "IR_DATASETS_HOME=$env:IR_DATASETS_HOME"
