import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


class SignatureService:
    def __init__(self, paths):
        self.paths = paths

    def store(self, source: str | Path | bytes) -> tuple[str, bool]:
        if isinstance(source, bytes):
            data = source
        else:
            path = Path(source)
            if not path.is_absolute():
                path = self.paths.signatures / path
            if not path.is_file():
                raise ValueError("签名图片不存在，请重新选择")
            if path.stat().st_size > 10_000_000:
                raise ValueError("签名图片不能超过 10 MB")
            data = path.read_bytes()
        if len(data) > 10_000_000:
            raise ValueError("签名图片不能超过 10 MB")
        with Image.open(BytesIO(data)) as original:
            if original.width * original.height > 25_000_000:
                raise ValueError("签名图片像素过大")
            pic = ImageOps.exif_transpose(original).convert("RGBA")
            pic.thumbnail((1600, 800))
            result = BytesIO()
            pic.save(result, format="PNG")
        data = result.getvalue()
        filename = hashlib.sha256(data).hexdigest() + ".png"
        target = self.paths.signatures / filename
        created = not target.exists()
        if created:
            temp = target.with_suffix(".tmp")
            temp.write_bytes(data)
            temp.replace(target)
        return filename, created
