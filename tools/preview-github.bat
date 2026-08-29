@echo off
rem ===========================================================================
rem  preview-github.bat  See a Markdown file exactly as GitHub will render it.
rem
rem  Ways to use it:
rem    1. Double click it in Explorer.        Previews every .md in the repo root.
rem    2. Drag .md files onto it.             Previews just those files.
rem    3. Run it from a terminal.             tools\preview-github.bat doc.md
rem    4. Offline, no network call.           tools\preview-github.bat /offline
rem
rem  The preview opens in your default browser. It uses GitHub's own renderer,
rem  so task lists, tables, autolinks and syntax colours match github.com.
rem
rem  Nothing is uploaded or published. The Markdown is posted to GitHub's
rem  rendering endpoint and the HTML comes straight back. Use /offline to avoid
rem  the network entirely, at the cost of a slightly less exact result.
rem ===========================================================================

setlocal EnableExtensions
title GitHub Markdown Preview

set "OPTIONS="

set "TOOLS_DIR=%~dp0"
set "VENV_DIR=%TOOLS_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "REQS=%TOOLS_DIR%requirements.txt"
set "SCRIPT=%TOOLS_DIR%github_preview.py"
set "RC=0"

rem --- Keep the window open when launched from Explorer. --------------------
set "KEEP_OPEN="
echo "%cmdcmdline%" | find /i "%~nx0" >nul 2>&1 && set "KEEP_OPEN=1"

rem --- Collect arguments, handling our own switches. -------------------------
set "ARGS="
:PARSE
if "%~1"=="" goto :PARSED
if /i "%~1"=="/offline" goto :OFFLINE
if /i "%~1"=="/nopause" goto :NOPAUSE
set "ARGS=%ARGS% "%~1""
shift
goto :PARSE
:OFFLINE
set "OPTIONS=%OPTIONS% --offline"
shift
goto :PARSE
:NOPAUSE
set "KEEP_OPEN="
set "OPTIONS=%OPTIONS% --no-open"
shift
goto :PARSE
:PARSED

echo ===============================================
echo   GitHub Markdown Preview
echo ===============================================
echo.

rem --- Make sure the virtual environment exists. ----------------------------
if exist "%VENV_PY%" goto :HAVE_VENV

echo [1/2] No virtual environment yet. Creating one, this happens only once.
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

%BOOTSTRAP% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo ERROR: the virtual environment could not be created.
    set "RC=1"
    goto :END
)

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
echo [1/2] Virtual environment found.
echo.

:RUN
echo [2/2] Rendering preview...
echo.
"%VENV_PY%" "%SCRIPT%"%OPTIONS%%ARGS%
if errorlevel 1 (
    echo.
    echo ERROR: the preview could not be generated. The message above says why.
    set "RC=1"
    goto :END
)

:END
echo.
if defined KEEP_OPEN (
    echo Press any key to close this window.
    pause >nul
)
exit /b %RC%
