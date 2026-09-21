"""Vista y controlador de escritorio."""

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from services.pipeline import NormalizationPipeline


class NormalizerApp:
    """UI mínima que mantiene la lógica fuera de la vista."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("ASTIN — Normalizador Inteligente de Metas")
        self.root.geometry("650x280")
        self.source = tk.StringVar()
        self.reference = tk.StringVar()
        self.destination = tk.StringVar(value=str(Path.cwd()))
        self.status = tk.StringVar(value="Seleccione el archivo de metas institucionales.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Archivo Excel de origen").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.source, width=62).grid(row=1, column=0, sticky="ew", pady=(2, 12))
        ttk.Button(frame, text="Examinar", command=self._select_source).grid(row=1, column=1, padx=(8, 0))
        ttk.Label(frame, text="Modelo normalizado de referencia (requerido para estructura exacta)").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.reference, width=62).grid(row=3, column=0, sticky="ew", pady=(2, 12))
        ttk.Button(frame, text="Examinar", command=self._select_reference).grid(row=3, column=1, padx=(8, 0))
        ttk.Label(frame, text="Carpeta de salida").grid(row=4, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.destination, width=62).grid(row=5, column=0, sticky="ew", pady=(2, 16))
        ttk.Button(frame, text="Examinar", command=self._select_destination).grid(row=5, column=1, padx=(8, 0))
        self.process = ttk.Button(frame, text="Normalizar y exportar", command=self._start)
        self.process.grid(row=6, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.status, wraplength=600).grid(row=7, column=0, columnspan=2, sticky="w", pady=(20, 0))
        frame.columnconfigure(0, weight=1)

    def _select_source(self) -> None:
        selected = filedialog.askopenfilename(filetypes=[("Libros Excel", "*.xlsx *.xlsm *.xls")])
        if selected:
            self.source.set(selected)

    def _select_destination(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self.destination.set(selected)

    def _select_reference(self) -> None:
        """Selecciona un libro modelo que sirve sólo para inferir el contrato."""
        selected = filedialog.askopenfilename(filetypes=[("Libros Excel", "*.xlsx *.xlsm *.xls")])
        if selected:
            self.reference.set(selected)

    def _start(self) -> None:
        if not self.source.get() or not self.reference.get():
            messagebox.showwarning("Archivos requeridos", "Seleccione el archivo de metas y el modelo de referencia.")
            return
        self.process.configure(state=tk.DISABLED)
        self.status.set("Analizando estructura y construyendo modelo estrella…")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            reference = Path(self.reference.get()) if self.reference.get() else None
            result = NormalizationPipeline().run(Path(self.source.get()), Path(self.destination.get()), reference)
            self.root.after(0, lambda: self._success(result.output_path))
        except Exception as error:  # La UI debe mostrar errores recuperables al usuario.
            self.root.after(0, lambda: self._error(str(error)))

    def _success(self, output: Path) -> None:
        self.process.configure(state=tk.NORMAL)
        self.status.set(f"Proceso finalizado: {output}")
        messagebox.showinfo("Proceso finalizado", f"Archivo creado:\n{output}")

    def _error(self, error: str) -> None:
        self.process.configure(state=tk.NORMAL)
        self.status.set("El proceso no pudo finalizar.")
        messagebox.showerror("Error de normalización", error)

    def run(self) -> None:
        """Inicia el bucle de eventos."""
        self.root.mainloop()
