#!/usr/bin/env python3
"""Editor schede PNG: compila i campi, carica il ritratto, salva ed esporta il PDF."""
import datetime
import json
import shutil
import sys
import uuid
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import build_sheet as sheet

DATA_DIR = Path.home() / "SchedePNG"
VW = 240                                   # viewport ritratto (stesso rapporto del riquadro nel PDF)
VH = round(VW * sheet.PORTRAIT[3] / sheet.PORTRAIT[2])
EXPORT_W = 1000                            # larghezza in px del ritratto esportato
ABILITY = ("forza", "destrezza", "costituzione", "intelligenza", "saggezza", "carisma")
SAVES = ["Forza", "Destrezza", "Costituzione", "Intelligenza", "Saggezza", "Carisma"]
SKILLS = ["Acrobazia", "Addestrare Animali", "Arcano", "Atletica", "Furtività", "Indagare", "Inganno",
          "Intimidire", "Intrattenere", "Intuizione", "Medicina", "Natura", "Percezione", "Persuasione",
          "Rapidità di Mano", "Religione", "Sopravvivenza", "Storia"]

# righe del modulo: (campo, tipo[, righe|opzioni]) tipo: e=entry, t=text, n=numero, p=elenco con bonus
HEAD = [
    [("classe_livello", "e"), ("tipo_taglia", "e")],
    [("occupazione_storia", "t", 3)],
    [("aspetto", "t", 3)],
]
ROWS = [
    [("dote", "t", 2), ("ideale", "t", 2)],
    [("modi_fare", "t", 2), ("legame", "t", 2)],
    [("interazione", "t", 2), ("difetti_segreti", "t", 2)],
    [("conoscenze", "t", 2)],
    "Statistiche",
    [(n, "n") for n in ABILITY],
    [("ca", "n"), ("pf", "n"), ("velocita", "n"), ("armatura_fonte", "e")],
    [("tiri_salvezza", "p", SAVES)],
    [("abilita", "p", SKILLS)],
    [("sensi", "e"), ("linguaggi", "e")],
    "Capacità e azioni",
    [("azioni", "t", 8), ("incantesimi_giornalieri", "t", 8)],
    [("capacita_passive", "t", 6), ("equipaggiamento", "t", 6)],
    [("note", "t", 5)],
]


def wheel_dy(e):
    """Delta verticale di rotella/trackpad, in pixel circa (positivo = verso l'alto)."""
    if sys.platform != "darwin":
        return e.delta // 3                      # Windows: ±120 per scatto
    low = e.delta & 0xFFFF                       # macOS <TouchpadScroll>: dx nei 16 bit alti, dy nei bassi
    return low if low < 0x8000 else low - 0x10000


def title(name):
    return sheet.LABELS[name].capitalize() if len(sheet.LABELS[name]) > 3 else sheet.LABELS[name]


class Portrait(tk.Canvas):
    """Anteprima del ritratto: trascina per spostare, rotella o slider per zoomare."""

    def __init__(self, master):
        super().__init__(master, width=VW, height=VH, bg="#ddd", highlightthickness=1, highlightbackground="#999")
        self.img = self.path = None
        self.zoom, self.cx, self.cy = 1.0, .5, .5
        self.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag", (e.x, e.y)))
        self.bind("<B1-Motion>", self._pan)
        for ev in ("<MouseWheel>", "<TouchpadScroll>"):
            self.bind(ev, lambda e: (self.set_zoom(self.zoom * 1.02 ** max(-8, min(8, wheel_dy(e) // 4))), "break")[1])
        self.create_text(VW / 2, VH / 2, text="Nessuna immagine", fill="#666", tags="empty")

    def load(self, path):
        self.img = Image.open(path).convert("RGB")
        self.path = str(path)
        self.zoom, self.cx, self.cy = 1.0, .5, .5
        self.render()

    def clear(self):
        self.img = self.path = None
        self.delete("img")
        self.itemconfigure("empty", state="normal")

    def scale(self):
        iw, ih = self.img.size
        return max(VW / iw, VH / ih) * self.zoom

    def region(self, out_w=VW, out_h=VH):
        """Rettangolo (in px immagine) visibile nel viewport, con centro riportato dentro i limiti."""
        iw, ih = self.img.size
        rw, rh = VW / self.scale(), VH / self.scale()
        self.cx = min(max(self.cx, rw / 2 / iw), 1 - rw / 2 / iw)
        self.cy = min(max(self.cy, rh / 2 / ih), 1 - rh / 2 / ih)
        x0, y0 = self.cx * iw - rw / 2, self.cy * ih - rh / 2
        return (x0, y0, x0 + rw, y0 + rh)

    def render(self):
        if self.img is None:
            return
        self.itemconfigure("empty", state="hidden")
        self.delete("img")
        self._photo = ImageTk.PhotoImage(self.img.resize((VW, VH), Image.LANCZOS, box=self.region()))
        self.create_image(0, 0, image=self._photo, anchor="nw", tags="img")

    def set_zoom(self, z):
        self.zoom = min(max(z, 1.0), 6.0)
        if self.on_zoom:
            self.on_zoom(self.zoom)
        self.render()

    on_zoom = None

    def _pan(self, e):
        if self.img is None:
            return
        (px, py), self._drag = self._drag, (e.x, e.y)
        iw, ih = self.img.size
        self.cx -= (e.x - px) / self.scale() / iw
        self.cy -= (e.y - py) / self.scale() / ih
        self.render()

    def export(self):
        if self.img is None:
            return None
        return self.img.resize((EXPORT_W, round(EXPORT_W * VH / VW)), Image.LANCZOS, box=self.region())


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Schede PNG")
        self.geometry("1100x800")
        self.minsize(900, 600)
        DATA_DIR.mkdir(exist_ok=True)
        self.widgets = {}
        self.current_id = None
        self.chars = []
        self._snap = None
        self._build_toolbar()
        self._build_drawer()
        self._build_form()
        self.refresh_list()
        self.new()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

    # ---------- UI ----------
    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=6)
        bar.pack(side="top", fill="x")
        ttk.Button(bar, text="☰ Personaggi", command=self.toggle_drawer).pack(side="left")
        ttk.Button(bar, text="Nuovo", command=self.new).pack(side="left", padx=(12, 0))
        ttk.Button(bar, text="Salva", command=self.save).pack(side="left", padx=4)
        ttk.Button(bar, text="Elimina", command=self.delete).pack(side="left", padx=4)
        ttk.Button(bar, text="Esporta PDF", command=self.export).pack(side="right")
        self.status = ttk.Label(bar, text="", foreground="#666")
        self.status.pack(side="right", padx=12)

    def _build_drawer(self):
        self.drawer = ttk.Frame(self, padding=6, width=260)
        self.drawer_open = False
        ttk.Label(self.drawer, text="Personaggi salvati", font=("", 13, "bold")).pack(anchor="w")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(self.drawer, textvariable=self.search).pack(fill="x", pady=4)
        self.listbox = tk.Listbox(self.drawer, activestyle="none", exportselection=False)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def toggle_drawer(self):
        if self.drawer_open:
            self.drawer.pack_forget()
        else:
            self.drawer.pack(side="left", fill="y", before=self.scroll_host)
        self.drawer_open = not self.drawer_open

    def _build_form(self):
        self.scroll_host = ttk.Frame(self)
        self.scroll_host.pack(side="left", fill="both", expand=True)
        cv = tk.Canvas(self.scroll_host, highlightthickness=0)
        sb = ttk.Scrollbar(self.scroll_host, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        form = ttk.Frame(cv, padding=12)
        win = cv.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))
        cv.configure(yscrollincrement=1)
        self.scroll = lambda e: cv.yview_scroll(-wheel_dy(e) // 2, "units")
        for ev in ("<MouseWheel>", "<TouchpadScroll>"):
            self.bind_all(ev, self.scroll)

        # testata: nome + campi iniziali a sinistra, ritratto a destra
        head = ttk.Frame(form)
        head.pack(fill="x")
        left = ttk.Frame(head)
        left.pack(side="left", fill="both", expand=True)
        self._row(left, [("nome", "e")])
        self.widgets["nome"].configure(font=("", 16, "bold"))
        for row in HEAD:
            self._row(left, row)
        right = ttk.Frame(head, padding=(16, 0, 0, 0))
        right.pack(side="right", anchor="n")
        ttk.Label(right, text="Ritratto").pack(anchor="w")
        self.portrait = Portrait(right)
        self.portrait.pack()
        self.zoom_var = tk.DoubleVar(value=1.0)
        self.portrait.on_zoom = self.zoom_var.set
        ttk.Scale(right, from_=1, to=6, variable=self.zoom_var,
                  command=lambda v: self.portrait.set_zoom(float(v))).pack(fill="x", pady=4)
        btns = ttk.Frame(right)
        btns.pack(fill="x")
        ttk.Button(btns, text="Carica immagine…", command=self.load_image).pack(side="left")
        ttk.Button(btns, text="Rimuovi", command=self.portrait.clear).pack(side="left", padx=4)

        for row in ROWS:
            if isinstance(row, str):
                ttk.Separator(form).pack(fill="x", pady=(14, 4))
                ttk.Label(form, text=row, font=("", 14, "bold")).pack(anchor="w")
            else:
                self._row(form, row)

    def _row(self, parent, row):
        fr = ttk.Frame(parent)
        fr.pack(fill="x", pady=4)
        for i, spec in enumerate(row):
            name, kind = spec[0], spec[1]
            cell = ttk.Frame(fr)
            cell.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            fr.columnconfigure(i, weight=0 if kind == "n" else 1)
            ttk.Label(cell, text=title(name)).pack(anchor="w")
            if kind == "t":
                w = tk.Text(cell, height=spec[2], wrap="word", undo=True, highlightthickness=1,
                            highlightbackground="#bbb", relief="flat", padx=4, pady=2)
                for ev in ("<MouseWheel>", "<TouchpadScroll>"):  # scorre la pagina, non il riquadro
                    w.bind(ev, lambda e: (self.scroll(e), "break")[1])
            else:
                w = ttk.Entry(cell, width=6 if kind == "n" else 20,
                              justify="center" if kind == "n" else "left")
            w.pack(fill="x")
            self.widgets[name] = w
            if kind == "p":
                self._picker(cell, w, spec[2])

    def _picker(self, parent, entry, options):
        """Elenco a tendina + bonus: 'Aggiungi' accoda 'Nome +N' al campo (che resta modificabile)."""
        fr = ttk.Frame(parent)
        fr.pack(fill="x", pady=(3, 0))
        choice = ttk.Combobox(fr, values=options, state="readonly", width=20)
        choice.pack(side="left")
        bonus = ttk.Entry(fr, width=5, justify="center")
        bonus.pack(side="left", padx=4)

        def add(_=None):
            if not choice.get():
                return
            b = bonus.get().strip()
            if b and b[0] not in "+-":
                b = "+" + b
            item = f"{choice.get()} {b}".strip()
            entry.insert("end", (", " if entry.get().strip() else "") + item)
            choice.set("")
            bonus.delete(0, "end")
        bonus.bind("<Return>", add)
        ttk.Button(fr, text="Aggiungi", command=add).pack(side="left")

    # ---------- dati ----------
    def get(self):
        d = {}
        for name, w in self.widgets.items():
            d[name] = w.get("1.0", "end-1c") if isinstance(w, tk.Text) else w.get()
        return d

    def set(self, data):
        for name, w in self.widgets.items():
            v = data.get(name, "")
            if isinstance(w, tk.Text):
                w.delete("1.0", "end")
                w.insert("1.0", v)
            else:
                w.delete(0, "end")
                w.insert(0, v)

    def snapshot(self):
        p = self.portrait
        self._snap = (self.get(), p.path, p.zoom, round(p.cx, 4), round(p.cy, 4))

    def dirty(self):
        p = self.portrait
        return self._snap is not None and self._snap != (self.get(), p.path, p.zoom, round(p.cx, 4), round(p.cy, 4))

    def confirm_discard(self):
        return not self.dirty() or messagebox.askyesno("Modifiche non salvate", "Scartare le modifiche non salvate?")

    def new(self):
        if not self.confirm_discard():
            return
        self.current_id = None
        self.set({})
        self.portrait.clear()
        self.zoom_var.set(1.0)
        self.listbox.selection_clear(0, "end")
        self.snapshot()
        self.status.configure(text="Nuovo personaggio")

    def save(self):
        data = self.get()
        if not data["nome"].strip():
            messagebox.showwarning("Nome mancante", "Inserisci almeno il nome del personaggio.")
            return
        cid = self.current_id or uuid.uuid4().hex[:8]
        p = self.portrait
        image = None
        if p.path:
            src = Path(p.path)
            dst = DATA_DIR / f"{cid}{src.suffix.lower()}"
            if src.resolve() != dst.resolve():
                shutil.copy(src, dst)
                p.path = str(dst)
            image = dst.name
        rec = {"id": cid, "fields": data, "image": image, "zoom": p.zoom, "cx": p.cx, "cy": p.cy,
               "updated": datetime.datetime.now().isoformat(timespec="seconds")}
        (DATA_DIR / f"{cid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        self.current_id = cid
        self.snapshot()
        self.refresh_list()
        self.status.configure(text=f"Salvato: {data['nome']}")

    def load(self, cid):
        rec = json.loads((DATA_DIR / f"{cid}.json").read_text(encoding="utf-8"))
        self.current_id = cid
        self.set(rec["fields"])
        img = DATA_DIR / rec["image"] if rec.get("image") else None
        if img and img.exists():
            self.portrait.load(img)
            self.portrait.zoom, self.portrait.cx, self.portrait.cy = rec["zoom"], rec["cx"], rec["cy"]
            self.zoom_var.set(rec["zoom"])
            self.portrait.render()
        else:
            self.portrait.clear()
            self.zoom_var.set(1.0)
        self.snapshot()
        self.status.configure(text=f"Caricato: {rec['fields'].get('nome', '')}")

    def delete(self):
        if not self.current_id:
            return
        if not messagebox.askyesno("Elimina", "Eliminare definitivamente questo personaggio?"):
            return
        for f in DATA_DIR.glob(f"{self.current_id}.*"):
            f.unlink()
        self.current_id = None
        self.snapshot()
        self.new()
        self.refresh_list()

    def refresh_list(self):
        self.chars = []
        self._snap = None
        for f in DATA_DIR.glob("*.json"):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
                self.chars.append((rec["fields"].get("nome", "") or "(senza nome)",
                                   rec["fields"].get("classe_livello", ""), rec["id"]))
            except (ValueError, KeyError):
                continue
        q = self.search.get().lower()
        self.chars = sorted(c for c in self.chars if q in c[0].lower() or q in c[1].lower())
        self.listbox.delete(0, "end")
        for nome, classe, _ in self.chars:
            self.listbox.insert("end", f"{nome}  —  {classe}" if classe else nome)
        self.listbox.selection_clear(0, "end")
        for i, c in enumerate(self.chars):
            if c[2] == self.current_id:
                self.listbox.selection_set(i)

    def _on_select(self, _):
        sel = self.listbox.curselection()
        if not sel or self.chars[sel[0]][2] == self.current_id:
            return
        if not self.confirm_discard():
            self.refresh_list()
            return
        self.load(self.chars[sel[0]][2])

    # ---------- azioni ----------
    def load_image(self):
        path = filedialog.askopenfilename(title="Scegli il ritratto",
                                          filetypes=[("Immagini", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff")])
        if not path:
            return
        try:
            self.portrait.load(path)
            self.zoom_var.set(1.0)
        except OSError as e:
            messagebox.showerror("Immagine non valida", str(e))

    def export(self):
        data = self.get()
        out = filedialog.asksaveasfilename(title="Esporta PDF", defaultextension=".pdf",
                                           initialfile=(data["nome"].strip() or "Scheda PNG") + ".pdf",
                                           filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        try:
            sheet.build(out, data, self.portrait.export())
        except OSError as e:
            messagebox.showerror("Errore di esportazione", str(e))
            return
        self.status.configure(text=f"Esportato: {Path(out).name}")

    def quit_app(self):
        if self.confirm_discard():
            self.destroy()


if __name__ == "__main__":
    if sys.platform == "win32":
        try:  # testo nitido su schermi HiDPI
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()
