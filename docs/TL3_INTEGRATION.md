# TL3 Integration — 서버 API 연동 스펙

TL3 세그먼트를 서버에서 받아오는 방법.

---

## TLNK 컨테이너 레이아웃

    [0..3]   "TLNK"                   magic 0x54 0x4C 0x4E 0x4B
    [4]      version = 0x03
    [5..8]   headerLen (uint32 BE)
    [9..]    header JSON (UTF-8)
    [세그먼트 1]  ciphertext (AES-256-GCM, iv=[4B 0][8B n])
    [세그먼트 2]  ciphertext
    ...
    [세그먼트 N]  ciphertext

---

## 헤더 JSON 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| v | int | 버전 (3) |
| aead | str | "AES-256-GCM" |
| kdf | str | "HKDF-SHA-256" |
| kind | str | "music" / "video" / "document" |
| title | str | 곡 제목 |
| artist | str | 아티스트 |
| bpm | int | BPM |
| dur_sec | int | 길이(초) |
| fs | int | 샘플레이트 (예: 44100) |
| ch | int | 채널 수 |
| mp3 | obj | { N, seg_bytes, last_bytes, first_offset } |
| hash_mp3 | str | 원본 해시 |
| fid | str | 파일 ID |
| salt | str | KDF salt |
| lic_id | str | 라이선스 ID |
| rights | obj | 저작권자 정보 (아래) |

### rights 객체

| 필드 | 설명 |
|---|---|
| creator_id | 창작자 ID |
| creator_name | 창작자 이름 |
| creator_wallet | TON 지갑 |
| license_type | exclusive / non-exclusive 등 |
| isrc | ISRC 코드 |
| copyright_year | 저작권 연도 |
| country | 국가 코드 |
| additional_credits | 공동 창작자 배열 |
| rights_confirmed | 확인 여부 |

---

## 세그먼트 API

### 요청

    GET /api/v1/tl3/segment/:fid?n=<N>&session_id=<SID>

### 서버 처리 (참고)

1. TL 잔액 검증
2. 세션 상태 검증
3. T_{n-1} 확인 (스파인)
4. 창작자 PC에서 세그먼트 fetch (Range)
5. AES-256-GCM 복호화
6. T_n 갱신 + D1 저장
7. TL 차감
8. 평문 반환

### 응답

- Content-Type: application/octet-stream
- Body: PCM16 (1초 분량)
- Header: X-TL-Balance (남은 TL), X-TL-Seq (n)

### 에러 코드

| 코드 | 의미 |
|---|---|
| 400 | n 순서 위반 (스파인) |
| 401 | 세션 만료 |
| 402 | TL 부족 |
| 403 | 권한 없음 |
| 404 | 세그먼트 없음 |
| 500 | 창작자 PC 오프라인 |

---

## 클라이언트 구현 규칙 (원칙 2 준수)

- 반드시 n=1부터 순차 요청
- n 건너뛰기 금지
- 병렬 요청 금지 (스파인 위반)
- 각 응답의 X-TL-Seq를 검증

---

## 환경변수

    TL_SERVER_BASE=https://api.timelink.example
    TL_SESSION_ID=<발급받은 세션>
    TL_AUTH_TOKEN=<인증 토큰>

---

## 보안 주의사항

- 세그먼트 평문은 **메모리에서만** 다룸
- 디스크 저장 금지 (원칙 1)
- 파이프라인 종료 시 명시적 폐기
- 로그에 평문 PCM 기록 금지
