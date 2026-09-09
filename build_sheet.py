#!/usr/bin/env python3
"""Genera la scheda PNG in stile pergamena.

Uso da terminale: python3 build_sheet.py  -> scheda vuota compilabile.
Uso da codice:   build(percorso, dati, ritratto) -> scheda compilata (testo disegnato, ritratto incluso).
"""
import math
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT = "Scheda_PNG_Fantasy_v2.pdf"
W, H = A4
M = 28                       # margine cornice esterna
INK = HexColor("#6B3A2B")    # inchiostro bruno
PAPER = HexColor("#F7F2EA")  # fondo pagina
BOX = HexColor("#EEE6DC")    # fondo riquadri
L, R, G = 42, W - 42, 10     # colonna sinistra, destra, gap
COLW = (R - L - G) / 2
PORTRAIT = (362, 80, R - 362, 184)   # x, y_top, w, h del riquadro ritratto

LABELS = {
    "nome": "NOME", "classe_livello": "CLASSE / LIVELLO", "tipo_taglia": "CREATURA / TAGLIA",
    "occupazione_storia": "OCCUPAZIONE E STORIA", "aspetto": "ASPETTO",
    "dote": "DOTE", "ideale": "IDEALE", "modi_fare": "MODI DI FARE", "legame": "LEGAME",
    "interazione": "INTERAZIONE CON GLI ALTRI", "difetti_segreti": "DIFETTI O SEGRETI",
    "conoscenze": "CONOSCENZE UTILI",
    "forza": "FOR", "destrezza": "DES", "costituzione": "COS",
    "intelligenza": "INT", "saggezza": "SAG", "carisma": "CAR",
    "ca": "CA", "pf": "PF", "velocita": "VELOCITÀ", "armatura_fonte": "ARMATURA / FONTE",
    "tiri_salvezza": "TIRI SALVEZZA", "abilita": "ABILITÀ", "sensi": "SENSI", "linguaggi": "LINGUAGGI",
    "azioni": "AZIONI", "incantesimi_giornalieri": "INCANTESIMI E USI GIORNALIERI",
    "capacita_passive": "TRATTI, AURE E CAPACITÀ PASSIVE", "equipaggiamento": "ARMI, EQUIPAGGIAMENTO E OGGETTI",
    "note": "NOTE AGGIUNTIVE",
}

# font: Hoefler su macOS, Georgia su Windows, DejaVu su Linux
_FONTS = [
    ("/System/Library/Fonts/Supplemental/Hoefler Text.ttc", 0, 1),
    ("C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/georgiab.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"),
]
for spec in _FONTS:
    if Path(spec[0]).exists():
        if len(spec) == 3:
            pdfmetrics.registerFont(TTFont("Serif", spec[0], subfontIndex=spec[1]))
            pdfmetrics.registerFont(TTFont("SerifBlack", spec[0], subfontIndex=spec[2]))
        else:
            pdfmetrics.registerFont(TTFont("Serif", spec[0]))
            pdfmetrics.registerFont(TTFont("SerifBlack", spec[1]))
        break
else:
    sys.exit("Nessun font serif trovato: installa Georgia o DejaVu Serif")


def T(y):  # coordinate dall'alto -> reportlab
    return H - y


def spaced(c, cx, y, text, font, size, cs):
    """Testo centrato con spaziatura lettere."""
    tw = pdfmetrics.stringWidth(text, font, size) + cs * (len(text) - 1)
    t = c.beginText(cx - tw / 2, y)
    t.setFont(font, size)
    t.setCharSpace(cs)
    t.textOut(text)
    c.drawText(t)
    return tw


# ---------- ornamenti ----------
def spiral(c, x, y, r, a0=0.0, turns=1.6, ccw=True):
    p = c.beginPath()
    n = 40
    for i in range(n + 1):
        t = i / n
        ang = a0 + (1 if ccw else -1) * t * turns * 2 * math.pi
        rr = r * (1 - 0.85 * t)
        px, py = x + rr * math.cos(ang), y + rr * math.sin(ang)
        (p.moveTo if i == 0 else p.lineTo)(px, py)
    c.drawPath(p, stroke=1, fill=0)


def leaf(c, x, y, length, angle):
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.curveTo(length * .3, length * .32, length * .8, length * .22, length, 0)
    p.curveTo(length * .8, -length * .22, length * .3, -length * .32, 0, 0)
    c.drawPath(p, stroke=1, fill=1)
    c.restoreState()


def vine(c, x1, x2, y, step=24, leaf_len=7):
    """Linea decorativa orizzontale con foglioline alternate e ricci alle estremità."""
    c.setLineWidth(.8)
    p = c.beginPath()
    p.moveTo(x1, y)
    n = max(2, int((x2 - x1) / 4))
    for i in range(1, n + 1):
        t = i / n
        p.lineTo(x1 + (x2 - x1) * t, y + 1.2 * math.sin(t * math.pi * (x2 - x1) / step))
    c.drawPath(p, stroke=1, fill=0)
    x = x1 + step * .6
    k = 0
    while x < x2 - step * .5:
        leaf(c, x, y, leaf_len, 35 if k % 2 == 0 else -35)
        x += step
        k += 1
    spiral(c, x1 - 2, y + 4, 5, a0=-math.pi / 2, ccw=False)
    spiral(c, x2 + 2, y + 4, 5, a0=-math.pi / 2, ccw=True)


def corner(c, x, y, sx, sy):
    """Riccio d'angolo; sx,sy = direzione verso l'interno (±1)."""
    c.setLineWidth(.9)
    p = c.beginPath()
    p.moveTo(x, y + sy * 26)
    p.curveTo(x, y + sy * 8, x + sx * 8, y, x + sx * 26, y)
    c.drawPath(p, stroke=1, fill=0)
    spiral(c, x + sx * 17, y + sy * 17, 8, a0=math.atan2(-sy, -sx), ccw=(sx * sy < 0))
    a = math.degrees(math.atan2(sy, sx))
    leaf(c, x + sx * 6, y + sy * 6, 8, a)
    leaf(c, x + sx * 23, y + sy * 4, 6, a + 30 * sx * sy)
    leaf(c, x + sx * 4, y + sy * 23, 6, a - 30 * sx * sy)


def shield(c, cx, cy, s):
    p = c.beginPath()
    p.moveTo(cx - s, cy + s)
    p.lineTo(cx + s, cy + s)
    p.curveTo(cx + s, cy - s * .2, cx + s * .6, cy - s * .9, cx, cy - s * 1.2)
    p.curveTo(cx - s * .6, cy - s * .9, cx - s, cy - s * .2, cx - s, cy + s)
    p.close()
    return p


def heart(c, cx, cy, s):
    p = c.beginPath()
    p.moveTo(cx, cy - s)
    p.curveTo(cx - s * 1.7, cy + s * .1, cx - s * .9, cy + s * 1.35, cx, cy + s * .45)
    p.curveTo(cx + s * .9, cy + s * 1.35, cx + s * 1.7, cy + s * .1, cx, cy - s)
    p.close()
    return p


def banner(c, cx, cy, text, size=7.5, bold=False, left=None):
    """Etichetta in un cartiglio centrato in (cx, cy), oppure con bordo sinistro in `left`."""
    font = "SerifBlack" if bold else "Serif"
    tw = pdfmetrics.stringWidth(text, font, size) + .8 * (len(text) - 1)
    w, h = tw + 18, size + 7
    if left is not None:
        cx = left + w / 2
    c.setFillColor(PAPER)
    c.setLineWidth(.7)
    c.roundRect(cx - w / 2, cy - h / 2, w, h, h / 2, stroke=1, fill=1)
    spiral(c, cx - w / 2 - 3, cy, 4, a0=0, ccw=False)
    spiral(c, cx + w / 2 + 3, cy, 4, a0=math.pi, ccw=True)
    c.setFillColor(INK)
    spaced(c, cx, cy - size * .35, text, font, size, .8)


# ---------- riquadri + campi ----------
def box(c, x, y_top, w, h, label=None, label_size=7.5):
    y = T(y_top + h)
    c.setFillColor(BOX)
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 7, stroke=1, fill=1)
    c.setLineWidth(.4)
    c.roundRect(x + 2.5, y + 2.5, w - 5, h - 5, 5, stroke=1, fill=0)
    c.setFillColor(INK)
    if label:
        banner(c, 0, T(y_top), label, size=label_size, left=x + 12)


def field(c, name, x, y_top, w, h, size=10, multiline=False, top_pad=9):
    """Campo compilabile; se `c.data` ha un valore lo disegna come testo fisso."""
    value = c.data.get(name, "").strip()
    fx, fy, fw, fh = x + 5, T(y_top + h) + 5, w - 10, h - 5 - top_pad
    if not value:
        c.acroForm.textfield(
            name=name, tooltip=name, x=fx, y=fy, width=fw, height=fh,
            fontName="Helvetica", fontSize=size, textColor=INK, fillColor=None, borderColor=None,
            borderWidth=0, fieldFlags="multiline" if multiline else "", forceBorder=False)
        return
    c.setFont("Serif", size)
    c.setFillColor(INK)
    if not multiline:
        c.drawString(fx + 2, fy + (fh - size * .7) / 2, value)
        return
    y = fy + fh - size
    for para in value.splitlines():
        for line in simpleSplit(para, "Serif", size, fw - 4) or [""]:
            if y < fy:
                return
            c.drawString(fx + 2, y, line)
            y -= size * 1.25


def fbox(c, name, x, y_top, w, h, size=9, multiline=True, label_size=7.5):
    box(c, x, y_top, w, h, LABELS[name], label_size)
    field(c, name, x, y_top, w, h, size, multiline)


def icon_box(c, name, x, y_top, w, h, icon):
    """Riquadro con simbolo (scudo/cuore) a sinistra e campo numerico a destra."""
    box(c, x, y_top, w, h, LABELS[name], 6.5)
    cx, cy = x + 20, T(y_top + h / 2) - 3
    c.setFillColor(PAPER)
    c.setLineWidth(1)
    c.drawPath(icon(c, cx, cy, 11), stroke=1, fill=1)
    c.setLineWidth(.4)
    c.drawPath(icon(c, cx, cy, 8), stroke=1, fill=0)
    c.setFillColor(INK)
    field(c, name, x + 32, y_top, w - 32, h, size=16, top_pad=11)


def stat_ring(c, name, cx, cy_top, r, size=16):
    cy = T(cy_top)
    c.setFillColor(BOX)
    c.setLineWidth(1)
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setLineWidth(.5)
    c.circle(cx, cy, r - 3, stroke=1, fill=0)
    c.setFillColor(INK)
    banner(c, cx, T(cy_top - r), LABELS[name], size=6.5)
    value = c.data.get(name, "").strip()
    if value:
        c.setFont("SerifBlack", size)
        c.drawCentredString(cx, cy - size * .35, value)
        return
    s = r * 1.3
    c.acroForm.textfield(
        name=name, tooltip=LABELS[name], x=cx - s / 2, y=cy - s / 2, width=s, height=s,
        fontName="Helvetica-Bold", fontSize=size, textColor=INK, fillColor=None,
        borderColor=None, borderWidth=0, forceBorder=False)
    c._doc.idToObject["Annot.NUMBER%d" % c._annotationCount].dict["Q"] = 1  # testo centrato


def portrait_box(c, image):
    x, y_top, w, h = PORTRAIT
    box(c, x, y_top, w, h)
    if image is not None:
        c.saveState()
        p = c.beginPath()
        p.roundRect(x + 4, T(y_top + h) + 4, w - 8, h - 8, 4)
        c.clipPath(p, stroke=0, fill=0)
        c.drawImage(ImageReader(image), x + 4, T(y_top + h) + 4, w - 8, h - 8)
        c.restoreState()
    banner(c, 0, T(y_top), "RITRATTO", left=x + 12)  # sopra l'immagine


def frame(c, title):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(1.2)
    c.roundRect(M, M, W - 2 * M, H - 2 * M, 10, stroke=1, fill=0)
    c.setLineWidth(.4)
    c.roundRect(M + 4, M + 4, W - 2 * M - 8, H - 2 * M - 8, 7, stroke=1, fill=0)
    for sx, x in ((1, M + 6), (-1, W - M - 6)):
        for sy, y in ((1, M + 6), (-1, H - M - 6)):
            corner(c, x, y, sx, sy)
    tw = spaced(c, W / 2, T(56), title, "SerifBlack", 24, 2)
    vine(c, 70, W / 2 - tw / 2 - 18, T(50))
    vine(c, W / 2 + tw / 2 + 18, W - 70, T(50))


def footer(c, n):
    c.setFont("Serif", 7)
    c.setFillColor(INK)
    c.drawCentredString(W / 2, 17, f"Scheda compilabile · pagina {n} di 2")


def page1(c, image):
    frame(c, "SCHEDA PNG")
    fbox(c, "nome", L, 80, 303, 44, size=14, multiline=False)
    portrait_box(c, image)
    fbox(c, "classe_livello", L, 132, 146, 40, size=10, multiline=False)
    fbox(c, "tipo_taglia", 199, 132, 146, 40, size=10, multiline=False)
    fbox(c, "occupazione_storia", L, 181, 303, 40)
    fbox(c, "aspetto", L, 230, 303, 34)
    y = 281
    for a, b in (("dote", "ideale"), ("modi_fare", "legame"), ("interazione", "difetti_segreti")):
        fbox(c, a, L, y, COLW, 36)
        fbox(c, b, L + COLW + G, y, COLW, 36)
        y += 44
    fbox(c, "conoscenze", L, y, R - L, 36)
    # statistiche
    vine(c, L + 10, W / 2 - 60, T(466))
    vine(c, W / 2 + 60, R - 10, T(466))
    banner(c, W / 2, T(466), "STATISTICHE", size=9, bold=True)
    sp = (R - L) / 6
    for i, name in enumerate(("forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma")):
        stat_ring(c, name, L + sp * (i + .5), 513, 29)
    icon_box(c, "ca", L, 558, 112, 46, shield)
    icon_box(c, "pf", L + 122, 558, 112, 46, heart)
    fbox(c, "velocita", R - 84, 558, 84, 46, size=14, multiline=False, label_size=6.5)
    fbox(c, "armatura_fonte", L, 618, R - L, 30, multiline=False)
    fbox(c, "tiri_salvezza", L, 662, R - L, 30, multiline=False)
    fbox(c, "abilita", L, 706, R - L, 30, multiline=False)
    fbox(c, "sensi", L, 750, COLW, 30, multiline=False)
    fbox(c, "linguaggi", L + COLW + G, 750, COLW, 30, multiline=False)
    footer(c, 1)


def page2(c):
    frame(c, "CAPACITÀ E AZIONI")
    fbox(c, "azioni", L, 92, COLW, 288)
    fbox(c, "incantesimi_giornalieri", L + COLW + G, 92, COLW, 288)
    fbox(c, "capacita_passive", L, 396, COLW, 210)
    fbox(c, "equipaggiamento", L + COLW + G, 396, COLW, 210)
    fbox(c, "note", L, 622, R - L, 158)
    footer(c, 2)


def build(out=OUT, data=None, portrait=None):
    """Scrive il PDF. `data`: dict nome_campo -> testo; `portrait`: immagine PIL o None."""
    c = canvas.Canvas(str(out), pagesize=A4)
    c.data = data or {}
    c.setTitle(c.data.get("nome") or "Scheda PNG Fantasy compilabile")
    c.acroForm.extras["NeedAppearances"] = True
    page1(c, portrait)
    c.showPage()
    page2(c)
    c.save()


if __name__ == "__main__":
    build()
    print("scritto", OUT)
