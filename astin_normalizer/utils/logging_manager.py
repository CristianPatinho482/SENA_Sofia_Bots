"""Configuración de bitácora de aplicación."""

import logging
from pathlib import Path


class LoggerManager:
    """Crea un logger de archivo sin duplicar controladores."""

    @staticmethod
    def get_logger(log_dir: Path) -> logging.Logger:
        """Devuelve el logger configurado para una ejecución."""
        logger = logging.getLogger("astin_normalizer")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_dir / "astin_normalizer.log", encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        return logger
