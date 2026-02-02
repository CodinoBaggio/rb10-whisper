@echo off
@chcp 65001 > nul
echo Building rb10-whisper...

rem Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

rem Build with PyInstaller
rem --onefile: Single executable
rem --noconfirm: Overwrite existing directory
rem --name: Output file name
pyinstaller --onefile --noconfirm --noconsole --paths . --name "rb10-whisper" launcher.py

echo.
echo Build complete. Executable is in dist\rb10-whisper.exe
pause
