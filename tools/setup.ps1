# Create the Python virtual environment for the Markdown to PDF tool (PowerShell).
#
#   .\tools\setup.ps1              # core engine only (pure Python, always works)
#   .\tools\setup.ps1 -WeasyPrint  # also install WeasyPrint (needs GTK on Windows)
#
# Afterwards:
#   .\tools\.venv\Scripts\Activate.ps1
#   python tools\md2pdf.py github-ssh-setup.md --toc

[CmdletBinding()]
param(
    [switch]$WeasyPrint,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$ToolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir  = Join-Path $ToolsDir '.venv'
$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'

# Locate an interpreter: prefer the py launcher, fall back to python on PATH.
$Launcher = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Launcher = @('py', '-3')
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Launcher = @('python')
} else {
    throw 'No Python interpreter found. Install Python 3.9 or newer and retry.'
}

if ($Force -and (Test-Path $VenvDir)) {
    Write-Host "Removing existing virtual environment at $VenvDir"
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $PythonExe)) {
    Write-Host "Creating virtual environment in $VenvDir"
    & $Launcher[0] $Launcher[1..($Launcher.Count - 1)] -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed.' }
} else {
    Write-Host "Reusing existing virtual environment in $VenvDir"
}

Write-Host 'Upgrading pip'
& $PythonExe -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }

$Requirements = if ($WeasyPrint) {
    Join-Path $ToolsDir 'requirements-weasyprint.txt'
} else {
    Join-Path $ToolsDir 'requirements.txt'
}

Write-Host "Installing from $Requirements"
& $PythonExe -m pip install -r $Requirements
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }

Write-Host ''
& $PythonExe (Join-Path $ToolsDir 'md2pdf.py') --list-engines

Write-Host ''
Write-Host 'Done. Next steps:'
Write-Host '  .\tools\.venv\Scripts\Activate.ps1'
Write-Host '  python tools\md2pdf.py github-ssh-setup.md --toc'
