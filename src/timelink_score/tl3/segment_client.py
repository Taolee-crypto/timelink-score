"""TL3 세그먼트 클라이언트 — 서버 API 연동.

원칙 1 (TL 소진): 평문 PCM은 메모리에서만 처리, 디스크 캐시 없음.
원칙 2 (스파인): n=1부터 순차 요청만 허용. 건너뛰기/역순 금지.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterator

import httpx


class SpineViolationError(Exception):
    """스파인 위반: n 순서가 어긋났을 때."""


class TLBalanceError(Exception):
    """TL 부족 (402)."""


class SegmentFetchError(Exception):
    """세그먼트 fetch 실패."""


@dataclass
class SegmentClient:
    """TL3 세그먼트 순차 fetch 클라이언트."""

    base_url: str
    fid: str
    session_id: str
    auth_token: str | None = None
    timeout: float = 30.0

    _last_n: int = field(default=0, init=False, repr=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False)
    _balance: int | None = field(default=None, init=False, repr=False)

    @property
    def last_n(self) -> int:
        return self._last_n

    @property
    def balance(self) -> int | None:
        return self._balance

    def fetch(self, n: int) -> bytes:
        """n번째 세그먼트(1초 PCM16) 1개를 가져온다."""
        if n <= 0:
            raise SpineViolationError(f"n은 1 이상이어야 합니다: {n}")
        if n != self._last_n + 1:
            raise SpineViolationError(
                f"스파인 위반: n={n} 요청 불가. "
                f"다음 허용 n={self._last_n + 1} (마지막 성공: {self._last_n})"
            )

        resp = self._get(n)
        self._last_n = n
        self._balance = _parse_balance(resp.headers.get("X-TL-Balance"))

        server_seq = resp.headers.get("X-TL-Seq")
        if server_seq is not None and int(server_seq) != n:
            raise SpineViolationError(
                f"서버 seq 불일치: 요청 n={n}, 응답 X-TL-Seq={server_seq}"
            )

        return resp.content

    def iter_segments(self, total: int) -> Iterator[bytes]:
        """n=1..total 까지 순차적으로 세그먼트를 yield."""
        if total <= 0:
            raise ValueError(f"total은 1 이상이어야 합니다: {total}")
        for n in range(1, total + 1):
            yield self.fetch(n)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SegmentClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _get(self, n: int) -> httpx.Response:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers(),
            )

        url = f"/api/v1/tl3/segment/{self.fid}"
        params = {"n": n, "session_id": self.session_id}

        try:
            resp = self._client.get(url, params=params)
        except httpx.HTTPError as e:
            raise SegmentFetchError(f"세그먼트 n={n} 요청 실패: {e}") from e

        if resp.status_code == 402:
            raise TLBalanceError(
                f"TL 부족 (n={n}). 남은 TL: {resp.headers.get('X-TL-Balance')}"
            )
        if resp.status_code == 400:
            raise SpineViolationError(f"서버가 스파인 위반으로 거부: n={n}")
        if resp.status_code == 401:
            raise SegmentFetchError("세션 만료 (401). 재로그인 필요.")
        if resp.status_code == 403:
            raise SegmentFetchError("권한 없음 (403).")
        if resp.status_code == 404:
            raise SegmentFetchError(f"세그먼트 n={n} 없음 (404).")
        if resp.status_code == 500:
            raise SegmentFetchError("창작자 PC 오프라인 (500).")
        if resp.status_code >= 400:
            raise SegmentFetchError(
                f"세그먼트 fetch 실패: HTTP {resp.status_code} ({resp.text[:200]})"
            )

        return resp

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/octet-stream"}
        token = self.auth_token or os.environ.get("TL_AUTH_TOKEN")
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h


def _parse_balance(raw: str | None) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
