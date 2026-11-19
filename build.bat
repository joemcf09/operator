@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Operator - build

if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing. Run run.bat once first, then try again.
  pause & exit /b 1
)

echo Installing build tools...
".venv\Scripts\python" -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 ( echo Could not install PyInstaller. & pause & exit /b 1 )

echo.
echo Building the application...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
".venv\Scripts\pyinstaller" --noconfirm operator.spec
if not exist "dist\Operator\Operator.exe" (
  echo.
  echo Build failed. See the messages above.
  pause & exit /b 1
)
echo Built dist\Operator\Operator.exe

rem ---------------------------------------------------------------- installer
set "ISCC="
for %%P in (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) do if not defined ISCC if exist %%P set "ISCC=%%~P"

if not defined ISCC (
  echo.
  echo ============================================================
  echo   The application is built, but Inno Setup was not found so
  echo   no installer was produced.
  echo.
  echo   Install Inno Setup 6 from https://jrsoftware.org/isdl.php
  echo   and run this file again to get:
  echo       installer\Output\Operator-Setup-1.8.0.exe
  echo.
  echo   You can still ship dist\Operator as a plain folder: run
  echo   Operator.exe inside it.
  echo ============================================================
  echo.
  pause & exit /b 0
)

echo.
echo Building the installer with Inno Setup...
"%ISCC%" installer\operator.iss
if errorlevel 1 ( echo Installer build failed. & pause & exit /b 1 )

echo.
echo ============================================================
echo   Done.
echo     Application : dist\Operator\Operator.exe
echo     Installer   : installer\Output\Operator-Setup-1.8.0.exe
echo.
echo   Tip: make-installer.bat does all of this in one step and
echo   can fetch Inno Setup for you.
echo ============================================================
echo.
pause
