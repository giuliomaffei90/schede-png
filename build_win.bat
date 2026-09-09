@echo off
REM Crea "dist\Schede PNG.exe". Richiede Python 3 da python.org (con "tcl/tk" spuntato nell'installer).
cd /d "%~dp0"
python -m venv .venv || exit /b 1
.venv\Scripts\pip install -q reportlab pillow pyinstaller || exit /b 1
.venv\Scripts\pyinstaller --noconfirm --clean --windowed --onefile --name "Schede PNG" app.py || exit /b 1
echo Fatto: dist\Schede PNG.exe
pause
