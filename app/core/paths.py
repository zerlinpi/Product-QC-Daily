import os
import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / relative


class AppPaths:
    def __init__(self, root: Path | str | None = None):
        if root is None:
            default = Path(os.getenv("LOCALAPPDATA", Path.home() / ".local" / "share"))
            root = os.getenv("QC_DATA_DIR", str(default / "Product-QC-Daily"))
        self.root = Path(root).expanduser().resolve()
        for name in ("database", "backups", "exports", "logs", "signatures", "config"):
            folder = self.root / name
            folder.mkdir(parents=True, exist_ok=True)
            setattr(self, name, folder)
        self.db_file = self.database / "product_qc.db"
        self.template = resource_path("templates/成品日检表模板.xlsx")
