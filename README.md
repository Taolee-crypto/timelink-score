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

