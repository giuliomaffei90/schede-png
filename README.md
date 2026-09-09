# Schede PNG

Editor per schede di personaggi non giocanti: compila i campi, carica un ritratto
(trascina per spostarlo, rotella o cursore per lo zoom), salva ed esporta il PDF in stile pergamena.

## File
- `app.py` – l'applicazione (Tkinter).
- `build_sheet.py` – disegna il PDF; da solo genera la scheda vuota compilabile.
- `build_mac.sh` / `build_win.bat` – creano l'eseguibile (.app / .exe) con PyInstaller.

## Avviare da sorgente
Serve Python 3.11+ con Tkinter:
```
pip install reportlab pillow
python3 app.py
```

## Creare l'eseguibile
Serve Python 3.11+ con Tkinter. Ogni sistema compila il proprio eseguibile:
- **macOS**: `sh build_mac.sh` → `dist/Schede PNG.app`
- **Windows**: doppio clic su `build_win.bat` → `dist\Schede PNG.exe`
  (installa Python da python.org lasciando spuntato "tcl/tk and IDLE").

Il PDF usa Hoefler Text su macOS e Georgia su Windows; per un aspetto identico
sui due sistemi basta aggiungere un font libero (es. EB Garamond) alla lista `_FONTS` in `build_sheet.py`.

## Dati
I personaggi salvati sono in `~/SchedePNG/` (un `.json` più l'immagine per ciascuno):
copiando quella cartella si spostano su un altro computer.
