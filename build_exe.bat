@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem Always run from the project folder, even if launched by double-click.
cd /d "%~dp0"
if errorlevel 1 goto :change_dir_failed

set "PYTHON=.venv\Scripts\python.exe"
set "DATASET=data\Telco-Customer-Churn.csv"
set "ICON=assets\churnpilot.ico"

rem Avoid parenthesized IF blocks here. The user's folder path may contain
rem parentheses (for example, "New folder (8)"), which can confuse CMD parsing
rem when expanded inside a command block.
if not exist "%PYTHON%" goto :missing_python
if not exist "%DATASET%" goto :missing_dataset
if not exist "%ICON%" goto :missing_icon

echo [INFO] Installing project dependencies...
"%PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

echo [INFO] Installing PyInstaller...
"%PYTHON%" -m pip install pyinstaller pillow
if errorlevel 1 goto :failed

echo [INFO] Removing previous build output...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ChurnPilot-by-ashiix.spec" del /q "ChurnPilot-by-ashiix.spec"

echo [INFO] Building ChurnPilot by ashiix...
"%PYTHON%" -m PyInstaller --noconfirm --clean --onedir --windowed --name "ChurnPilot-by-ashiix" --icon "%ICON%" --add-data "data;data" --add-data "assets;assets" main.py
if errorlevel 1 goto :failed

 echo.
echo [SUCCESS] Build complete.
echo Executable location:
echo "%CD%\dist\ChurnPilot-by-ashiix\ChurnPilot-by-ashiix.exe"
 echo.
echo Keep the entire dist\ChurnPilot-by-ashiix folder together when sharing it.
pause
exit /b 0

:missing_python
echo.
echo [ERROR] Project virtual environment was not found:
echo   .venv\Scripts\python.exe
echo Run these commands from the project folder first:
echo   py -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1

:missing_dataset
echo.
echo [ERROR] Training dataset was not found.
echo Expected relative path: %DATASET%
echo Project folder:
cd
echo Copy the real Telco-Customer-Churn.csv into the data folder above.
echo The CSV is intentionally excluded from the ZIP and Git repository.
pause
exit /b 1

:missing_icon
echo.
echo [ERROR] Icon file was not found: %ICON%
echo Restore assets\churnpilot.ico and run this script again.
pause
exit /b 1

:change_dir_failed
echo [ERROR] Could not switch to the script folder.
pause
exit /b 1

:failed
echo.
echo [ERROR] Build failed. Review the error messages above.
pause
exit /b 1
