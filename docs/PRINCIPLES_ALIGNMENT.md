# PRINCIPLES Alignment — 6대 원칙 준수 매핑

TL_PRINCIPLES.md 6대 원칙과 본 모듈의 대응.

---

## 원칙 1: TL이 있는 만큼만 사용 가능

**원칙:** TL 소진 = 파일 무력화.

**본 모듈 대응:**
- 세그먼트는 스트리밍 처리, 캐싱 없음
- 파이프라인 종료 시 PCM 즉시 폐기
- TL 부족 시 (서버 402) 즉시 중단 + 사용자 고지

**코드 위치:** `tl3/segment_client.py`, `pipeline.py`

---

## 원칙 2: 스파인 기능

**원칙:** 순방향만 매끄러움. 역방향/우회 시 손상.

**본 모듈 대응:**
- 세그먼트 요청 n=1부터 순차 강제
- `SegmentClient`가 내부 상태로 `last_n` 추적
- n 건너뛰기, 역순 요청 시 예외
- 응답 헤더 X-TL-Seq 검증

**코드 위치:** `tl3/segment_client.py` (SpineViolationError)

---

## 원칙 3: LP 및 확장 기능은 별도 모듈

**원칙:** TL 파일 = 순수 원본. 확장은 별도 모듈.

**본 모듈 대응:**
- 본 레포 = **분석/악보 생성 확장 모듈**
- 재생 기능 없음 (재생은 lp.js 등 별도)
- 출력물은 MusicXML / PDF / MIDI

**코드 위치:** 전체 (재생 코드 없음)

---

## 원칙 4: 저장 위치 = 창작자 PC

**원칙:** TL 파일 원본 = 창작자 PC. 서버 = 중계자.

**본 모듈 대응:**
- 원본 TL3 저장 안 함
- 서버 중계로 받은 평문만 일시 사용
- `output/`에는 분석 결과만 저장

**코드 위치:** `tl3/segment_client.py` (메모리 스트림)

---

## 원칙 5: TLNK 컨테이너

**원칙:** 모든 타입 공통 컨테이너.

**본 모듈 대응:**
- 헤더 파서가 magic + version 검증
- `kind`가 "music"인지 확인
- 세그먼트는 서버가 복호화 (우리는 ciphertext 다루지 않음)

**코드 위치:** `tl3/header_parser.py`

---

## 원칙 6: 저작권자 정보 삽입

**원칙:** 모든 TL 파일에 저작권자 정보 암호학적 포함.

**본 모듈 대응:**
- 헤더 `rights` 객체를 악보 상단에 자동 삽입
- creator_name, ISRC, copyright_year, country 표기
- additional_credits (공동 창작자)도 반영
- meta.json에 원본 rights 저장

**코드 위치:** `rights/attribution.py`, `score/builder.py`

---

## 원칙 위반 시나리오 (금지)

| 시나리오 | 위반 원칙 | 이유 |
|---|---|---|
| 세그먼트 디스크 캐싱 | 1 | TL 소진 후에도 사용 가능해짐 |
| n=5부터 요청 | 2 | 스파인 우회 |
| 재생 기능 내장 | 3 | 확장 모듈 경계 위반 |
| 원본 TL3 저장 | 4 | 창작자 소유권 침해 |
| ciphertext 직접 복호화 시도 | 5 | master_secret 없이는 불가 |
| rights 정보 누락 | 6 | 저작권자 귀속 위반 |

---

## 검증 체크리스트

배포 전 확인:

- [ ] 캐시 파일 생성 코드 없음
- [ ] 세그먼트 n 순서 강제 로직 존재
- [ ] 재생 관련 코드 없음
- [ ] 원본 TL3 저장 코드 없음
- [ ] 헤더 파서가 magic/version 검증
- [ ] 악보에 rights 정보 포함

---

## 참고

- TL_PRINCIPLES.md (timelink-backend)
- 특허 출원 10-2025-0167813
