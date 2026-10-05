"""Create JPEG upload copies with checked publication metadata."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from PIL import Image, ImageEnhance, ImageStat

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "photoshop": "http://ns.adobe.com/photoshop/1.0/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
}
for prefix, uri in NS.items():
    ElementTree.register_namespace(prefix, uri)


def _publication_time(value: str) -> datetime:
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("실제 게시 시각에는 시간대 오프셋이 필요합니다.")
    return moment


def _packet(source_xmp: bytes | None, published_at: str, address: str) -> bytes:
    root = ElementTree.fromstring(source_xmp.strip()) if source_xmp else ElementTree.Element(f"{{{NS['rdf']}}}RDF")
    description = root.find(f".//{{{NS['rdf']}}}Description")
    if description is None:
        description = ElementTree.SubElement(root, f"{{{NS['rdf']}}}Description")
    description.set(f"{{{NS['dc']}}}source", address)
    description.set(f"{{{NS['photoshop']}}}Instructions", f"게시 장소: {address}")
    description.set(f"{{{NS['xmp']}}}MetadataDate", published_at)
    return ElementTree.tostring(root, encoding="utf-8")


def _publication_exif(source_exif: bytes | None, moment: datetime, address: str) -> bytes:
    exif = Image.Exif()
    if source_exif:
        exif.load(source_exif)
    capture_time = moment.strftime("%Y:%m:%d %H:%M:%S")
    exif[306] = capture_time  # DateTime
    exif[36867] = capture_time  # DateTimeOriginal
    exif[36868] = capture_time  # DateTimeDigitized
    exif[37521] = f"{moment.microsecond:06d}"  # SubsecTimeOriginal
    exif[36880] = moment.strftime("%z")[:3] + ":" + moment.strftime("%z")[3:]  # OffsetTime
    exif[36881] = exif[36880]  # OffsetTimeOriginal
    exif[36882] = exif[36880]  # OffsetTimeDigitized
    exif[37510] = b"UNICODE\x00" + f"사진 장소: {address}".encode("utf-16-be")  # UserComment
    gps = exif.get_ifd(34853)
    gps.clear()
    gps[27] = b"UNICODE\x00" + address.encode("utf-16-be")  # GPSAreaInformation, address not coordinates
    exif[34853] = gps
    return exif.tobytes()


def prepare_photo(
    source: Path,
    destination: Path,
    *,
    published_at: str,
    address: str,
    enhance: bool = False,
) -> dict[str, str]:
    moment = _publication_time(published_at)
    if not address.strip():
        raise ValueError("게시 장소 주소가 비어 있습니다.")
    if source.resolve() == destination.resolve() or destination.exists():
        raise FileExistsError(f"원본 또는 기존 파일은 덮어쓰지 않습니다: {destination}")
    with Image.open(source) as image:
        if image.format != "JPEG":
            raise ValueError(f"JPEG 사진만 지원합니다: {source}")
        xmp = image.info.get("xmp")
        exif = _publication_exif(image.info.get("exif"), moment, address)
        icc = image.info.get("icc_profile")
        image.load()
        output_image = image
        if enhance:
            luminance = ImageStat.Stat(image.convert("L").resize((64, 64))).mean[0]
            brightness = min(1.14, max(1.0, 110 / max(luminance, 1)))
            output_image = ImageEnhance.Brightness(image).enhance(brightness)
            output_image = ImageEnhance.Contrast(output_image).enhance(1.04)
        destination.parent.mkdir(parents=True, exist_ok=True)
        output_image.save(
            destination,
            format="JPEG",
            quality=95,
            xmp=_packet(xmp, moment.isoformat(), address),
            exif=exif,
            icc_profile=icc or b"",
        )
    with Image.open(destination) as result:
        packet = result.info.get("xmp")
        if not packet:
            destination.unlink()
            raise RuntimeError("출력 사진에서 XMP를 읽을 수 없습니다.")
        root = ElementTree.fromstring(packet)
        description = root.find(f".//{{{NS['rdf']}}}Description")
        if (
            description is None
            or description.get(f"{{{NS['dc']}}}source") != address
            or description.get(f"{{{NS['xmp']}}}MetadataDate") != moment.isoformat()
        ):
            destination.unlink()
            raise RuntimeError("출력 사진의 XMP가 요청 값과 다릅니다.")
        output_exif = result.getexif()
        exif_valid = (
            output_exif.get(36867) != moment.strftime("%Y:%m:%d %H:%M:%S")
            or output_exif.get(37510) != b"UNICODE\x00" + f"사진 장소: {address}".encode("utf-16-be")
            or output_exif.get_ifd(34853).get(27) != b"UNICODE\x00" + address.encode("utf-16-be")
        )
    if exif_valid:
        destination.unlink()
        raise RuntimeError("출력 사진의 EXIF 촬영 시각 또는 장소가 요청 값과 다릅니다.")
    return {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": str(destination),
        "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "publication_time": moment.isoformat(),
        "publication_location": address,
        "enhanced": str(enhance).lower(),
    }


def prepare_photo_plan(
    plan_path: Path,
    output_dir: Path,
    *,
    published_at: str,
    address: str,
    enhance: bool = False,
) -> list[dict[str, str]]:
    _publication_time(published_at)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    slots = plan.get("slots")
    if not isinstance(slots, list) or not slots:
        raise ValueError("게시할 사진 슬롯이 필요합니다.")
    selected: list[tuple[Path, str]] = []
    for slot in slots:
        if not isinstance(slot, dict):
            raise ValueError("사진 슬롯 형식이 올바르지 않습니다.")
        processed = slot.get("processed")
        path = processed.get("output") if isinstance(processed, dict) else None
        path = path or slot.get("processed_file") or slot.get("file")
        if not isinstance(path, str) or not Path(path).is_file():
            raise FileNotFoundError(f"사진 슬롯 파일이 없습니다: {path}")
        scene = slot.get("scene") or slot.get("description") or slot.get("asset_description")
        if not isinstance(scene, str) or not scene.strip():
            raise ValueError(f"장면 설명이 없는 사진 슬롯은 이름을 만들 수 없습니다: {path}")
        name = re.sub(r"[^0-9A-Za-z가-힣]+", "_", scene.strip()).strip("_")
        if not name:
            raise ValueError(f"파일명에 사용할 수 없는 장면 설명입니다: {scene}")
        selected.append((Path(path), name[:60].rstrip("_")))
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"기존 게시 사진 폴더는 덮어쓰지 않습니다: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        prepare_photo(path, output_dir / f"{index:02d}_{name}.jpg", published_at=published_at, address=address, enhance=enhance)
        for index, (path, name) in enumerate(selected, 1)
    ]
