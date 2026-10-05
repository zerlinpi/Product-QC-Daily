import hashlib
import posixpath
import re
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook

REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def file_sha256(path: Path, chunk_size=1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_compatible(path: Path):
    """Repair invalid WPS chart references in memory; never change the source."""
    buffer = BytesIO()
    with ZipFile(path) as original, ZipFile(buffer, "w", ZIP_DEFLATED) as target:
        if sum(i.file_size for i in original.infolist()) > 250_000_000:
            raise ValueError("工作簿解压后过大，请拆分后导入")
        for entry in original.infolist():
            data = original.read(entry.filename)
            if re.fullmatch(r"xl/charts/chart\d+\.xml", entry.filename):
                root = ET.fromstring(data)
                for parent in root.iter():
                    for node in list(parent):
                        if node.tag.endswith("}externalData"):
                            parent.remove(node)
                data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            target.writestr(entry.filename, data)
    buffer.seek(0)
    return load_workbook(buffer, data_only=False)


def wps_images(path: Path) -> dict[str, bytes]:
    with ZipFile(path) as archive:
        if "xl/cellimages.xml" not in archive.namelist():
            return {}
        rels = ET.fromstring(archive.read("xl/_rels/cellimages.xml.rels"))
        targets = {
            r.get("Id"): posixpath.normpath(posixpath.join("xl", r.get("Target", ""))) for r in rels
        }
        result = {}
        for pic in ET.fromstring(archive.read("xl/cellimages.xml")).iter():
            if not pic.tag.endswith("}pic"):
                continue
            name = next((n.get("name") for n in pic.iter() if n.tag.endswith("}cNvPr")), None)
            embed = next(
                (n.get(f"{{{REL}}}embed") for n in pic.iter() if n.tag.endswith("}blip")), None
            )
            target = targets.get(embed, "")
            if name and target.startswith("xl/media/") and target in archive.namelist():
                if archive.getinfo(target).file_size <= 10_000_000:
                    result[name] = archive.read(target)
        return result


def write_text(cell, value) -> None:
    """Treat user values as text even when they start with '='."""
    cell.value = value
    if isinstance(value, str):
        cell.data_type = "s"
