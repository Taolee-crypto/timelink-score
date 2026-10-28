## TRACK 보컬 멜로디 + 가사 악보 (2026-10-29 수정)

**사용자가 원하는 것은 보컬 선율과 실제 등록 가사가 음표 아래 붙은 악보입니다.**
혼합 음원에 YIN을 바로 적용하면 드럼과 베이스를 멜로디로 오인하기 때문에 이 방식은 폐기했습니다.

`src/timelink_score/vocal_score.py`는 다음을 실제로 수행하도록 분리했습니다.

1. Demucs `htdemucs`로 보컬과 나머지 반주 분리 — 모델을 사용할 수 없으면 중단
2. `torchcrepe`로 **분리된 vocals.wav**의 유효한 성대 음정만 추출 — 음성 없는 구간은 쉼표 유지
3. WhisperX의 **한국어 강제 정렬 모델**을 사용해 보컬에 등록된 가사의 단어별 시간 계산 — 인식 가사가 원본과 다르면 중단
4. 실제 가창 음표 타임라인에 가사 음절 배치하고 music21 MusicXML에 노랫말 출력
5. 비공개 검수 초안 JSON + MusicXML 출력; TLD 봉인·TL 과금 없음

### 분석 서버 조건

Cloudflare Workers의 일반 JS 실행 환경에서 Demucs/WhisperX/TorchCrepe 모델을 실행하는 구조는 구현되어 있지 않습니다.
별도 GPU 분석 서버에서 `pip install -e '.[vocal-inference]'`로 모델을 설치하고, 서버에서 **검증된 V5 곡 소스/등록 가사**를 권한 확인 후 안전하게 전달하는 연동이 필요합니다.
현재 파이프라인의 `scripts/transcribe_vocals.py`는 관리자 개발 테스트용이며 TRACK 사용자는 음원을 다시 업로드할 필요가 없습니다.
모델 다운로드·한국어 노래 실측 정확도·안전한 V5 분석 작업 연동은 아직 검증되지 않았습니다.

### 출력 주의

노래의 바이브라토·합창·코러스·애드립과 다중 음절/한 음의 가사는 사람이 최종 검수해야 합니다.
WhisperX가 실제 가사를 다른 단어로 인식하면 **자동으로 맞춰서 그럴듯한 가사를 만들지 않고 실패**합니다.
모의 모델 MusicXML+한글 가사 테스트가 통과해도 실제 노래에서의 정확도가 검증된 것은 아닙니다.

---
# TimeLink Score — TRACK 악보 분석 엔진

## V5 악보 생성 재개 (2026-10-29)

이 프로젝트는 TRACK의 실제 오디오 입력을 받아 MusicXML 악보와 TRACK 호환 ScoreData를 만드는 엔진입니다. 이전에 누락된 pipeline.py를 복구했습니다.

- 사용자가 권리를 가진 WAV/MP3/FLAC/M4A/OGG를 로컬에서 분석합니다.
- torchcrepe가 있으면 모델 기반, 없으면 librosa YIN 추정으로 멜로디를 추출합니다.
- 기존 코드 진행·조성 분석과 music21 리드시트 엔진을 연결합니다.
- MusicXML/track-score-draft.json/meta.json을 출력합니다. PDF는 설치된 LilyPond가 있을 때 선택적으로 생성합니다.
- 정식 TLD 암호화·판매·정산은 아직 미구현이며 이 기능은 TL을 차감하지 않습니다.
- 구형 V3 TL3 세그먼트 자동 분석은 V5 인증 체계와 다르므로 현재 금지합니다.

### 설치와 실행 (Python 3.11)

```bash
python -m pip install 'numpy>=1.24,<2' 'scipy>=1.11' 'librosa>=0.10.2' 'soundfile>=0.12.1' 'music21>=9.1'
PYTHONPATH=src python scripts/transcribe_local.py song.wav --out output/my-song --bpm 90
```

Windows PowerShell은 `$env:PYTHONPATH='src'`를 지정한 뒤 `python scripts/transcribe_local.py song.wav --bpm 90`로 실행합니다.

MusicXML은 편집 가능한 악보 초안이며 복잡한 믹스 음원은 수동 검수가 필요합니다. 원본 음원은 출력 폴더에 복제하지 않습니다. V5 TL3 재생 음원 자동 분석에는 권리 확인·분석 세션·서버 처리 및 TLD 발행 연동이 추가로 필요합니다.

---
# TimeLink Score

**TL3 음원 파일에서 오선지 악보를 자동 생성하는 확장 모듈.**



**# TimeLink Score**



**\*\*TL3 음원 파일에서 오선지 악보를 자동 생성하는 확장 모듈.\*\***



**TimeLink의 TL\_PRINCIPLES.md 6대 원칙을 준수합니다.**



**---**



**## 개요**



**TL3(시간 충전형 음원) 파일을 입력받아:**



**- 멜로디 → 오선지 악보 (MusicXML / PDF)**

**- 조성(장조/단조) + 조표(샵/플랫) 자동 판별**

**- (예정) 가사 정렬**

**- (예정) 애드립 라인 분리**

**- 원칙 6: 저작권자 정보를 악보에 자동 표기**



**---**



**## TL 원칙 준수 매핑**



**| 원칙 | 본 모듈의 대응 |**

**|---|---|**

**| 1. TL 소진 = 무력화 | 캐싱 없음, 세그먼트 스트리밍 처리 |**

**| 2. 스파인 기능 | 순방향(n=1→N) 세그먼트 요청만 허용 |**

**| 3. 확장 모듈 | 본 레포는 별도 확장 모듈 (재생 X, 분석 O) |**

**| 4. 원본은 창작자 PC | 원본 저장 없음, 서버 중계만 이용 |**

**| 5. TLNK 컨테이너 | 헤더 파서 + 세그먼트 클라이언트 |**

**| 6. 저작권자 정보 | 악보 상단에 creator/ISRC 자동 삽입 |**



**자세한 내용: docs/PRINCIPLES\_ALIGNMENT.md**



**---**



**## 설치**



&#x20;   **git clone https://github.com/Taolee-crypto/timelink-score.git**

&#x20;   **cd timelink-score**

&#x20;   **python -m venv venv**

&#x20;   **source venv/bin/activate   # Windows: venv\\Scripts\\activate**

&#x20;   **pip install -r requirements.txt**



**외부 도구 (악보 PDF 렌더링):**

**- MuseScore 4 설치 후 mscore --version 확인**



**---**



**## 사용 예시**



**### 헤더만 파싱 (TL 소모 없음)**



&#x20;   **python scripts/parse\_header\_only.py song.tl3**



&#x20;   **from timelink\_score.tl3 import parse\_header**



&#x20;   **meta = parse\_header("song.tl3")**

&#x20;   **print(meta\["title"], meta\["bpm"], meta\["rights"]\["creator\_name"])**



**### 전체 파이프라인 (TL 소모 발생)**



&#x20;   **python scripts/run\_all.py song.tl3 --out output/score.pdf**



**⚠️ 세그먼트 요청 시 TL이 차감됩니다. 사용자 동의 필요.**



**---**



**## 프로젝트 구조**



&#x20;   **timelink-score/**

&#x20;   **├── docs/                      # 설계/스펙 문서**

&#x20;   **├── src/timelink\_score/        # 핵심 패키지**

&#x20;   **│   ├── tl3/                   # TLNK 헤더 파서 + 세그먼트 클라이언트**

&#x20;   **│   ├── audio/                 # Demucs 보컬 분리, PCM 이어붙이기**

&#x20;   **│   ├── pitch/                 # Basic Pitch → MIDI**

&#x20;   **│   ├── key/                   # 조성 분석**

&#x20;   **│   ├── score/                 # music21 악보 생성, PDF 렌더링**

&#x20;   **│   ├── rights/                # 원칙 6: 저작권자 정보 삽입**

&#x20;   **│   └── pipeline.py            # 전체 오케스트레이션**

&#x20;   **├── scripts/                   # CLI 진입점**

&#x20;   **├── tests/                     # 테스트**

&#x20;   **└── examples/                  # 사용 예제**



**---**



**## 로드맵**



**- \[x] Step 0: 프로젝트 스캐폴딩**

**- \[ ] Step 1: TLNK 헤더 파서 (평문 JSON)**

**- \[ ] Step 2: 세그먼트 클라이언트 (서버 API 연동)**

**- \[ ] Step 3: Demucs 보컬 분리**

**- \[ ] Step 4: Basic Pitch → MIDI**

**- \[ ] Step 5: 조성 분석 + 조표**

**- \[ ] Step 6: music21 악보 생성 + PDF 렌더링**

**- \[ ] Step 7: 저작권자 정보 삽입 (원칙 6)**

**- \[ ] Step 8: 가사 정렬 (WhisperX)**

**- \[ ] Step 9: 애드립 라인 분리 (반자동)**



**---**



**## 특허**



**본 모듈은 TimeLink 특허 출원 \*\*10-2025-0167813\*\* ("시간 충전형 디지털 파일 기반 창작자 수익 창출, AI 예측 및 대출 연계 통합 시스템")의 부속 확장 모듈입니다.**



**---**



**## 라이선스**



**(미정 — TimeLink 프로젝트 정책에 따름)**

