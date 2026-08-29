@echo off
rem ===========================================================================
rem  make-pdf.bat  Generate PDFs from the Markdown files in this repository.
rem
rem  Ways to use it:
rem    1. Double click it in Explorer.        Converts every .md in the repo root.
rem    2. Drag .md files onto it.             Converts just those files.
rem    3. Run it from a terminal.             tools\make-pdf.bat doc.md
rem    4. Run it from a script.               tools\make-pdf.bat /nopause doc.md
rem
rem  The first run creates tools\.venv and installs the dependencies. Later runs
rem  reuse it and finish in a second or two. PDFs are written to tools\out.
rem
rem  To change the rendering options, edit the OPTIONS line below.
rem ===========================================================================

setlocal EnableExtensions
title Markdown to PDF

set "OPTIONS=--toc"

set "TOOLS_DIR=%~dp0"
set "VENV_DIR=%TOOLS_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQS=%TOOLS_DIR%requirements.txt"
set "SCRIPT=%TOOLS_DIR%md2pdf.py"
set "OUT_DIR=%TOOLS_DIR%out"
set "RC=0"

rem --- Keep the window open when the file was launched from Explorer. --------
set "KEEP_OPEN="
echo "%cmdcmdline%" | find /i "%~nx0" >nul 2>&1 && set "KEEP_OPEN=1"

rem --- Collect arguments, pulling out our own /nopause switch. ---------------
set "ARGS="
:PARSE
if "%~1"=="" goto :PARSED
if /i "%~1"=="/nopause" goto :SKIPARG
set "ARGS=%ARGS% "%~1""
shift
goto :PARSE
:SKIPARG
set "KEEP_OPEN="
shift
goto :PARSE
:PARSED

echo ===============================================
echo   Markdown to PDF
echo ===============================================
echo.

rem --- Step 1: make sure the virtual environment exists. --------------------
if exist "%VENV_PY%" goto :HAVE_VENV

echo [1/3] No virtual environment yet. Creating one, this happens only once.
echo.

set "BOOTSTRAP="
py -3 --version >nul 2>&1 && set "BOOTSTRAP=py -3"
if not defined BOOTSTRAP (
    python --version >nul 2>&1 && set "BOOTSTRAP=python"
)

if not defined BOOTSTRAP (
    echo ERROR: Python was not found on this machine.
    echo.
    echo Install Python 3.9 or newer from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" during the installation.
    set "RC=1"
    goto :END
)

echo       Creating %VENV_DIR%
%BOOTSTRAP% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ERROR: the virtual environment could not be created.
    set "RC=1"
    goto :END
)

echo.
echo [2/3] Installing dependencies. This takes a minute the first time.
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PY%" -m pip install -r "%REQS%" --quiet
if errorlevel 1 (
    echo ERROR: the dependencies could not be installed.
    set "RC=1"
    goto :END
)
echo       Done.
echo.
goto :RUN

:HAVE_VENV
echo [1/3] Virtual environment found.
echo [2/3] Dependencies already installed.
echo.

rem --- Step 3: convert. -----------------------------------------------------
:RUN
echo [3/3] Generating PDF...
echo.
"%VENV_PY%" "%SCRIPT%" %OPTIONS%%ARGS%
if errorlevel 1 (
    echo.
    echo ERROR: PDF generation failed. The message above says why.
    set "RC=1"
    goto :END
)

echo.
echo Output folder: %OUT_DIR%
if defined KEEP_OPEN start "" "%OUT_DIR%"

:END
echo.
if defined KEEP_OPEN (
    echo Press any key to close this window.
    pause >nul
)
exit /b %RC%
