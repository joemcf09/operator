@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Operator - Ferry, Cargo & ACMI

rem ---------------------------------------------------------------- find Python
set "PY="

rem 1) the py launcher (installed with python.org builds, ignores Store aliases)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY=py -3"
)

rem 2) python on PATH, but only if it is real and not the Microsoft Store stub
if not defined PY (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined PY (
      echo %%P | find /i "WindowsApps" >nul
      if errorlevel 1 (
        "%%P" -c "import sys" >nul 2>nul
        if not errorlevel 1 set "PY=%%P"
      )
    )
  )
)

rem 3) common install locations
if not defined PY (
  for %%D in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe"
    "%ProgramFiles%\Python313\python.exe" "%ProgramFiles%\Python312\python.exe" "%ProgramFiles%\Python311\python.exe"
  ) do (
    if not defined PY if exist %%D set "PY=%%D"
  )
)

if not defined PY (
  echo.
  echo ============================================================
  echo   Python was not found.
  echo.
  echo   Install Python 3.10 or newer from:
  echo       https://www.python.org/downloads/windows/
  echo   During setup, tick "Add python.exe to PATH".
  echo.
  echo   Do NOT use the Microsoft Store shortcut - that is what
  echo   produced the message you just saw.
  echo.
  echo   Then run this file again.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

echo Using Python: %PY%
%PY% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
  echo.
  echo Python 3.10 or newer is required. Please update Python and try again.
  echo.
  pause
  exit /b 1
)

rem ---------------------------------------------------------------- environment
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python environment, this takes a minute the first time...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo Could not create the environment. If this folder is inside OneDrive or
    echo Program Files, try moving it somewhere simple like C:\Operator.
    echo.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  echo Installing dependencies...
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Dependency installation failed. Check your internet connection and
    echo any firewall or proxy, then run this file again.
    echo.
    pause
    exit /b 1
  )
)

if /i "%~1"=="--setup-only" (
  echo Environment ready.
  exit /b 0
)

rem ---------------------------------------------------------------- run
echo.
echo Starting Operator. Leave this window open while you play.
echo Close it to shut the program down.
echo.
".venv\Scripts\python.exe" server.py
echo.
echo Operator has stopped.
pause
