"""CLI for preparing publication copies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import prepare_photo, prepare_photo_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="원본을 보존하며 사진 보정·장면 파일명·XMP 게시 맥락을 준비합니다.")
    parser.add_argument("source", type=Path, help="JPEG 사진 또는 photo_plan.json")
    parser.add_argument("destination", type=Path, help="새 JPEG 파일 또는 비어 있는 출력 폴더")
    parser.add_argument("--address", required=True, help="확인된 게시 장소 주소 (촬영 GPS가 아님)")
    parser.add_argument("--published-at", required=True, help="실제 게시 시각, ISO 8601 시간대 포함")
    parser.add_argument("--enhance", action="store_true", help="어두운 사진에만 약한 밝기·대비 보정")
    args = parser.parse_args()
    if args.source.suffix.lower() == ".json":
        result = prepare_photo_plan(
            args.source, args.destination, published_at=args.published_at, address=args.address, enhance=args.enhance
        )
    else:
        result = prepare_photo(
            args.source, args.destination, published_at=args.published_at, address=args.address, enhance=args.enhance
        )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
