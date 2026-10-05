from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest
from PIL import Image, ImageStat

CORE_PATH = Path(__file__).resolve().parents[1] / "src" / "photo_enhancement_pack" / "core.py"
SPEC = importlib.util.spec_from_file_location("photo_enhancement_core", CORE_PATH)
assert SPEC is not None and SPEC.loader is not None
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
NS = core.NS
prepare_photo = core.prepare_photo
prepare_photo_plan = core.prepare_photo_plan

ADDRESS = "서울 중구 예시로 10"
PUBLISHED_AT = "2026-10-05T12:20:00+09:00"


def _sample(path: Path) -> None:
    image = Image.new("RGB", (24, 16), (17, 42, 88))
    exif = Image.Exif()
    exif[36867] = "2024:04:05 12:30:00"
    image.save(path, exif=exif)


def test_copy_preserves_capture_and_writes_publication_context(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    output = tmp_path / "upload.jpg"
    _sample(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    result = prepare_photo(source, output, published_at=PUBLISHED_AT, address=ADDRESS)

    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert result["source_sha256"] == before
    with Image.open(output) as image:
        assert image.getexif().get(36867) == "2024:04:05 12:30:00"
        packet = ElementTree.fromstring(image.info["xmp"])
    entry = packet.find(f".//{{{NS['rdf']}}}Description")
    assert entry is not None
    assert entry.get(f"{{{NS['dc']}}}source") == ADDRESS
    assert entry.get(f"{{{NS['xmp']}}}MetadataDate") == PUBLISHED_AT


def test_plan_uses_scene_names_and_preserves_sources(tmp_path: Path) -> None:
    sources = [tmp_path / f"photo{index}.jpg" for index in range(2)]
    for source in sources:
        _sample(source)
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"slots": [{"file": str(source), "scene": f"입구 장면 {index}"} for index, source in enumerate(sources, 1)]}),
        encoding="utf-8",
    )

    result = prepare_photo_plan(plan, tmp_path / "prepared", published_at=PUBLISHED_AT, address=ADDRESS)

    assert [Path(item["output"]).name for item in result] == ["01_입구_장면_1.jpg", "02_입구_장면_2.jpg"]
    assert all(hashlib.sha256(source.read_bytes()).hexdigest() == item["source_sha256"] for source, item in zip(sources, result))


def test_missing_scene_does_not_create_output(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    _sample(source)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"slots": [{"file": str(source)}]}), encoding="utf-8")
    output = tmp_path / "prepared"

    with pytest.raises(ValueError, match="장면 설명"):
        prepare_photo_plan(plan, output, published_at=PUBLISHED_AT, address=ADDRESS)

    assert not output.exists()


def test_enhancement_is_optional_and_preserves_exif(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    plain = tmp_path / "plain.jpg"
    enhanced = tmp_path / "enhanced.jpg"
    _sample(source)

    prepare_photo(source, plain, published_at=PUBLISHED_AT, address=ADDRESS)
    prepare_photo(source, enhanced, published_at=PUBLISHED_AT, address=ADDRESS, enhance=True)

    with Image.open(plain) as original, Image.open(enhanced) as adjusted:
        assert ImageStat.Stat(adjusted.convert("L")).mean[0] > ImageStat.Stat(original.convert("L")).mean[0]
        assert adjusted.getexif().get(36867) == "2024:04:05 12:30:00"
        assert adjusted.info["xmp"] == original.info["xmp"]
