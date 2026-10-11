# Architecture — timelink-score

TL3 파일 → 오선지 악보 파이프라인 설계.

---

## 전체 파이프라인

    [TL3 파일]
        |
        v
    (1) 헤더 파싱 (평문 JSON)          ← tl3/header_parser.py
        |   bpm, dur_sec, title, rights 등 추출
        v
    (2) 세그먼트 순방향 요청            ← tl3/segment_client.py
        |   GET /api/v1/tl3/segment/:id?n=1..N
        |   서버가 복호화한 PCM 평문 수신
        v
    (3) PCM 이어붙이기                  ← audio/pcm_concat.py
        |   → vocals_or_mix.wav
        v
    (4) 보컬 분리 (Demucs)              ← audio/separate.py
        |   → vocals.wav
        v
    (5) 피치 + 온셋 → MIDI              ← pitch/extract.py
        |   Basic Pitch
        v
    (6) 조성 분석                       ← key/analyze.py
        |   Krumhansl-Schmuckler
        v
    (7) 악보 생성                       ← score/builder.py
        |   music21 (조표, 박자, 음표 배치)
        v
    (8) 저작권자 정보 삽입              ← rights/attribution.py
        |   원칙 6: creator, ISRC, copyright
        v
    (9) PDF 렌더링                      ← score/render.py
        |   MuseScore CLI
        v
    [score.pdf]

---

## 모듈 책임

| 모듈 | 책임 | 의존 |
|---|---|---|
| tl3/header_parser | TLNK 헤더(평문 JSON) 파싱 | 없음 (표준 라이브러리) |
| tl3/segment_client | 서버 API 세그먼트 fetch | httpx |
| audio/pcm_concat | 세그먼트 PCM → WAV | soundfile, numpy |
| audio/separate | 보컬/반주 분리 | demucs |
| pitch/extract | 피치 → MIDI | basic-pitch |
| key/analyze | 조성 판별 | librosa, numpy |
| score/builder | MusicXML 생성 | music21 |
| score/render | MusicXML → PDF | MuseScore CLI |
| rights/attribution | 저작권 메타 삽입 | 없음 |
| pipeline | 전체 오케스트레이션 | 위 전체 |

---

## 데이터 흐름 (원칙 준수)

### 원칙 1: TL 소진 = 무력화
- 세그먼트는 **메모리 스트림**으로 처리, 디스크 캐시 없음
- 파이프라인 종료 시 모든 PCM 폐기

### 원칙 2: 스파인 (순방향)
- 세그먼트 요청은 반드시 `n=1, 2, 3, ...` 순차
- `segment_client`에서 **n 순서 검증** 강제
- 역방향/건너뛰기 시 즉시 예외 발생

### 원칙 3: 확장 모듈
- 본 레포는 **분석/악보 생성**만 담당
- 재생 기능 없음
- 출력물: MusicXML, PDF, (선택) MIDI

### 원칙 4: 원본은 창작자 PC
- 원본 TL3를 저장하지 않음
- 서버 중계로 받은 평문만 일시 사용

### 원칙 5: TLNK 컨테이너
- 헤더 파서가 TLNK magic(0x54 0x4C 0x4E 0x4B) + version 검증
- 세그먼트는 서버가 복호화 → 우리는 ciphertext 다루지 않음

### 원칙 6: 저작권자 정보
- 헤더의 `rights` 객체를 악보 상단에 자동 삽입
- creator_name, ISRC, copyright_year 등

---

## 출력물

| 파일 | 용도 |
|---|---|
| output/score.musicxml | 중간 산출물 (편집 가능) |
| output/score.pdf | 최종 악보 |
| output/score.mid | (선택) MIDI |
| output/meta.json | 헤더 메타 + 저작권 정보 |

---

## 실패 지점과 대응

| 지점 | 증상 | 대응 |
|---|---|---|
| 헤더 파싱 실패 | magic 불일치 | 명확한 에러 메시지 |
| 세그먼트 순서 위반 | 서버 400/403 | n 순차 강제 |
| TL 부족 | 서버 402/429 | 사용자 고지 후 중단 |
| 피치 추출 노이즈 | MIDI 스퓨리어스 | 후처리 (min duration 필터) |
| MuseScore 미설치 | CLI 없음 | 설치 안내 |

---

## 확장 포인트

- `pitch/extract.py`: Basic Pitch 외 다른 모델로 교체 가능
- `key/analyze.py`: 딥러닝 기반 조성 분석으로 교체 가능
- `score/builder.py`: LilyPond 등 다른 렌더러 지원 가능
- Step 8, 9 (가사, 애드립) 추가 예정
