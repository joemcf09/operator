@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title Operator - build installer
set "VER=1.8.0"

echo.
echo  ============================================================
echo    Operator - installer build
echo  ============================================================
echo.

rem ---------------------------------------------------------------- 1. Python env
if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creating the Python environment...
  call run.bat --setup-only
  if not exist ".venv\Scripts\python.exe" (
    echo.
    echo Could not create the Python environment. Run run.bat once and make sure
    echo the program starts, then try again.
    pause & exit /b 1
  )
) else (
  echo [1/4] Python environment found.
)

rem ---------------------------------------------------------------- 2. build tools
echo [2/4] Installing build tools...
".venv\Scripts\python" -m pip install --quiet --upgrade pyinstaller
if errorlevel 1 ( echo Could not install PyInstaller. & pause & exit /b 1 )

rem ---------------------------------------------------------------- 3. application
echo [3/4] Building the application (this takes a couple of minutes)...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
".venv\Scripts\pyinstaller" --noconfirm --log-level WARN operator.spec
if not exist "dist\Operator\Operator.exe" (
  echo.
  echo Build failed - see the messages above.
  pause & exit /b 1
)
echo       dist\Operator\Operator.exe

rem ---------------------------------------------------------------- 4. installer
set "ISCC="
for %%P in (
  "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
  "%ProgramFiles%\Inno Setup 6\ISCC.exe"
  "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) do if not defined ISCC if exist %%P set "ISCC=%%~P"

if not defined ISCC (
  echo [4/4] Inno Setup was not found.
  where winget >nul 2>nul
  if not errorlevel 1 (
    choice /c YN /m "      Install Inno Setup 6 now with winget"
    if !errorlevel! equ 1 (
      winget install --id JRSoftware.InnoSetup -e --accept-package-agreements --accept-source-agreements
      for %%P in (
        "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
        "%ProgramFiles%\Inno Setup 6\ISCC.exe"
        "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
      ) do if not defined ISCC if exist %%P set "ISCC=%%~P"
    )
  )
)

if not defined ISCC (
  echo.
  echo  ------------------------------------------------------------
  echo   The application is built but no installer was produced.
  echo   Install Inno Setup 6 from https://jrsoftware.org/isdl.php
  echo   and run this file again.
  echo.
  echo   You can still ship dist\Operator as a portable folder.
  echo  ------------------------------------------------------------
  echo.
  pause & exit /b 0
)

echo [4/4] Compiling the installer...
"%ISCC%" /Q installer\operator.iss
if errorlevel 1 ( echo Installer build failed. & pause & exit /b 1 )

rem ---------------------------------------------------------------- upload bundles
echo       Assembling the upload packages...
copy /y docs\README.txt      dist\Operator\ >nul
copy /y docs\FIRST-RUN.txt   dist\Operator\ >nul
copy /y docs\CHANGELOG.txt   dist\Operator\ >nul
copy /y LICENSE.txt           dist\Operator\ >nul

rem 1) installer wrapped in a zip - most upload sites reject or quarantine a bare .exe
if exist "installer\Output\setupbundle" rmdir /s /q "installer\Output\setupbundle"
mkdir "installer\Output\setupbundle"
copy /y "installer\Output\Operator-Setup-%VER%.exe" "installer\Output\setupbundle\" >nul
copy /y docs\README.txt      "installer\Output\setupbundle\" >nul
copy /y docs\FIRST-RUN.txt   "installer\Output\setupbundle\" >nul
copy /y docs\CHANGELOG.txt   "installer\Output\setupbundle\" >nul
copy /y LICENSE.txt           "installer\Output\setupbundle\" >nul
powershell -NoProfile -Command "Compress-Archive -Path 'installer\Output\setupbundle\*' -DestinationPath 'installer\Output\Operator-%VER%-Windows-Installer.zip' -Force"
rmdir /s /q "installer\Output\setupbundle"

rem 2) portable: the same build, no installation
powershell -NoProfile -Command "Compress-Archive -Path 'dist\Operator\*' -DestinationPath 'installer\Output\Operator-%VER%-Windows-Portable.zip' -Force"

rem 3) source: runs on Windows, macOS and Linux via run.bat / run.sh
if exist "installer\Output\src" rmdir /s /q "installer\Output\src"
mkdir "installer\Output\src\Operator"
robocopy . "installer\Output\src\Operator" /E /XD .venv build dist installer save __pycache__ .git /XF operator-log.txt *.pyc >nul
powershell -NoProfile -Command "Compress-Archive -Path 'installer\Output\src\Operator' -DestinationPath 'installer\Output\Operator-%VER%-Source-CrossPlatform.zip' -Force"
rmdir /s /q "installer\Output\src"

powershell -NoProfile -Command "Get-ChildItem 'installer\Output\*.zip','installer\Output\*.exe' | Get-FileHash -Algorithm SHA256 | ForEach-Object { $_.Hash + '  ' + (Split-Path $_.Path -Leaf) } | Set-Content 'installer\Output\SHA256SUMS.txt'"

echo.
echo  ============================================================
echo    Done. Upload packages in installer\Output:
echo.
echo      Operator-%VER%-Windows-Installer.zip     <- upload this one
echo      Operator-%VER%-Windows-Portable.zip      no installation needed
echo      Operator-%VER%-Source-CrossPlatform.zip  macOS and Linux
echo      SHA256SUMS.txt                           checksums for all of them
echo.
echo    Raw installer: installer\Output\Operator-Setup-%VER%.exe
echo  ============================================================
echo.
explorer "installer\Output"
pause
