# 사진보강팩 (Photo Enhancement Pack)

JPEG 사진의 **게시용 사본**을 만들 때 약한 밝기·대비 보정, 확인된 장면으로 만든 파일명, XMP 게시 장소·시각 기록을 함께 수행하는 Python CLI입니다. 원본은 수정하지 않습니다.

제작: **더장사 아카데미 승기**. Python CLI이므로 Claude, Codex, GPT 등 특정 AI 실행기에 종속되지 않습니다.

## 설치

Python 3.11 이상이 필요합니다. 이 팩 저장소의 루트에서 `py -3 -m pip install .`을 실행합니다. 의존성은 Pillow입니다.

## 사진 한 장

```powershell
photo-enhance source.jpg publish-copy.jpg --address "서울 중구 예시로 10" --published-at "2026-10-05T12:20:00+09:00" --enhance
```

`--enhance`를 생략하면 사진을 보정하지 않습니다. 어두운 사진의 밝기를 최대 14% 높이고 대비를 4% 조정합니다. 자동으로 화이트밸런스, 메뉴 색상, 피사체를 생성하거나 변경하지 않습니다. 최종 사용 전 원본과 나란히 눈으로 비교하세요.

## 여러 장과 장면 파일명

실제로 확인한 장면을 `scene`에 기록합니다. 원본 파일명이나 과거 라벨만으로 장면을 추측하지 않습니다.

```json
{
  "slots": [
    {"file": "photos/entrance.jpg", "scene": "매장 입구 간판"},
    {"file": "photos/table.jpg", "scene": "창가 나무 테이블"}
  ]
}
```

```powershell
photo-enhance photo_plan.json publish-copies --address "서울 중구 예시로 10" --published-at "2026-10-05T12:20:00+09:00" --enhance
```

출력 예: `01_매장_입구_간판.jpg`, `02_창가_나무_테이블.jpg`. JSON 결과에 원본·사본 SHA-256과 게시 맥락을 기록합니다. 기존 출력 파일이나 비어 있지 않은 폴더는 덮어쓰지 않습니다. 입력 사진은 JPEG여야 합니다.

## 메타데이터의 의미

- 지정한 게시 시각을 출력 사본의 EXIF `DateTime`, `DateTimeOriginal`, `DateTimeDigitized`와 XMP `MetadataDate`에 기록합니다. 원본 사진의 실제 촬영 시각과 다른 값이 되며, 게시 시각에는 시간대 오프셋이 필요합니다.
- 주소를 EXIF `UserComment`·`GPSAreaInformation` 및 XMP `dc:source`·`photoshop:Instructions`에 기록합니다. 기존 GPS 좌표는 사본에서 제거합니다. 주소만으로 위도·경도를 추정해 생성하지 않으므로 지도 앱의 좌표 위치 표시는 보장하지 않습니다.
- 원본 파일은 보존하지만 출력 사본의 촬영 시각·위치 정보는 게시 맥락에 맞춰 바뀝니다. 이전 촬영 정보가 필요하면 원본을 참조하세요.
- 사진의 사용 권리와 장면은 사용자가 확인해야 합니다. `--enhance`는 AI 생성 콘텐츠 판별을 바꾸는 기능이 아닙니다.
- 플랫폼은 업로드 후 파일명이나 XMP를 재작성·제거할 수 있습니다. 업로드 사본과 공개 이미지의 메타데이터는 별도로 검사하세요.

## 테스트

```powershell
py -3 -m pip install -e ".[test]"
py -3 -m pytest tests
```

## 라이선스

MIT. 저작권 © 2026 더장사 아카데미 승기.
