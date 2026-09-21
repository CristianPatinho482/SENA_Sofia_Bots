from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .settings import RESOURCE_ROOT, SofiaCredentials


DEFAULT_ICON_PATH = RESOURCE_ROOT / "assets" / "SOFIABOT.png"
DEFAULT_BANNER_PATH = RESOURCE_ROOT / "assets" / "BOT_REPORTES.png"
BANNER_MAX_SIZE = (260, 260)


@dataclass(frozen=True)
class CredentialsDialogResult:
    """Resultado del cuadro de credenciales."""

    credentials: SofiaCredentials | None
    cancelled: bool


class CredentialsDialog:
    """Cuadro simple para pedir usuario y clave sin guardarlos en disco."""

    def __init__(
        self,
        icon_path: str | Path = DEFAULT_ICON_PATH,
        banner_path: str | Path = DEFAULT_BANNER_PATH,
    ) -> None:
        self.icon_path = Path(icon_path)
        self.banner_path = Path(banner_path)
        self.result = CredentialsDialogResult(credentials=None, cancelled=True)

        self.root = tk.Tk()
        self.root.title("SOFIABOT - Credenciales")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.cancel)

        self.usuario = tk.StringVar()
        self.password = tk.StringVar()
        self.icon_image: tk.PhotoImage | None = None
        self.banner_image: tk.PhotoImage | None = None

        self._build_ui()
        self._center()

    def _load_banner(self) -> tk.PhotoImage | None:
        """Carga BOT_REPORTES.png y lo reduce a BANNER_MAX_SIZE si es necesario."""
        candidates = [self.banner_path]
        # Compatibilidad: si aun no existe el banner nuevo, usa el icono anterior.
        if self.icon_path not in candidates:
            candidates.append(self.icon_path)
        for candidate in candidates:
            try:
                if not candidate.exists():
                    continue
                # Intento con Pillow para escalar con calidad.
                try:
                    from PIL import Image, ImageTk

                    img = Image.open(candidate).convert("RGBA")
                    img.thumbnail(BANNER_MAX_SIZE, Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.banner_image = photo
                    return photo
                except Exception:
                    pass
                # Fallback sin Pillow: PhotoImage + subsample entero.
                photo = tk.PhotoImage(file=str(candidate))
                factor = max(1, photo.width() // BANNER_MAX_SIZE[0], photo.height() // BANNER_MAX_SIZE[1])
                if factor > 1:
                    photo = photo.subsample(factor, factor)
                self.banner_image = photo
                return photo
            except Exception:
                continue
        return None

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.grid(row=0, column=0, sticky="nsew")

        banner = self._load_banner()
        if banner is not None:
            banner_label = ttk.Label(frame, image=banner)
            banner_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        if self.icon_path.exists():
            try:
                self.icon_image = tk.PhotoImage(file=str(self.icon_path))
                self.root.iconphoto(True, self.icon_image)
            except Exception:
                pass

        title = ttk.Label(frame, text="BOT REPORTES - Registro de Tiempo", font=("Segoe UI", 13, "bold"))
        title.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))

        subtitle = ttk.Label(frame, text="Ingreso a Sofia Plus")
        subtitle.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="Usuario").grid(row=3, column=0, columnspan=3, sticky="w")
        user_entry = ttk.Entry(frame, textvariable=self.usuario, width=40)
        user_entry.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(2, 10))

        ttk.Label(frame, text="Contraseña").grid(row=5, column=0, columnspan=3, sticky="w")
        password_entry = ttk.Entry(frame, textvariable=self.password, width=40, show="*")
        password_entry.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(2, 14))

        cancel_button = ttk.Button(frame, text="Cancelar", command=self.cancel)
        cancel_button.grid(row=7, column=1, sticky="e", padx=(0, 8))

        start_button = ttk.Button(frame, text="Ejecutar", command=self.accept)
        start_button.grid(row=7, column=2, sticky="e")

        self.root.bind("<Return>", lambda _event: self.accept())
        self.root.bind("<Escape>", lambda _event: self.cancel())
        user_entry.focus_set()

    def _center(self) -> None:
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        self.root.geometry(f"+{x}+{y}")

    def accept(self) -> None:
        usuario = self.usuario.get().strip()
        password = self.password.get().strip()
        if not usuario or not password:
            messagebox.showwarning(
                "Credenciales incompletas",
                "Ingresa usuario y contraseña para continuar.",
                parent=self.root,
            )
            return

        self.result = CredentialsDialogResult(
            credentials=SofiaCredentials(usuario=usuario, password=password),
            cancelled=False,
        )
        self.root.destroy()

    def cancel(self) -> None:
        self.result = CredentialsDialogResult(credentials=None, cancelled=True)
        self.root.destroy()

    def show(self) -> CredentialsDialogResult:
        self.root.mainloop()
        return self.result


def ask_credentials(
    icon_path: str | Path = DEFAULT_ICON_PATH,
    banner_path: str | Path = DEFAULT_BANNER_PATH,
) -> SofiaCredentials | None:
    """Muestra el cuadro de credenciales y retorna None si el usuario cancela."""
    return CredentialsDialog(icon_path=icon_path, banner_path=banner_path).show().credentials
