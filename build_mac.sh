#!/bin/sh
# Crea "dist/Schede PNG.app". Richiede Python 3 con Tkinter (python.org o brew python-tk).
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/pip install -q reportlab pillow pyinstaller
.venv/bin/pyinstaller --noconfirm --clean --windowed --name "Schede PNG" app.py
echo "Fatto: dist/Schede PNG.app"
