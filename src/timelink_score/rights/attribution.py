"""저작권자 정보 삽입 — 원칙 6.

TL 헤더의 rights 객체:
    creator_id, creator_name, creator_wallet,
    license_type, isrc, copyright_year, country,
    additional_credits, rights_confirmed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from music21 import metadata


@dataclass
class CreatorAttribution:
    """저작권자 귀속 정보."""

    creator_name: str = ""
    creator_id: int | None = None
    creator_wallet: str = ""
    license_type: str = ""
    isrc: str = ""
    copyright_year: int | None = None
    country: str = ""
    additional_credits: list[dict[str, Any]] = field(default_factory=list)
    rights_confirmed: bool = False

    @classmethod
    def from_tl_rights(cls, rights: dict[str, Any] | None) -> "CreatorAttribution":
        if not rights:
            return cls()
        return cls(
            creator_name=str(rights.get("creator_name", "")),
            creator_id=rights.get("creator_id"),
            creator_wallet=str(rights.get("creator_wallet", "")),
            license_type=str(rights.get("license_type", "")),
            isrc=str(rights.get("isrc", "")),
            copyright_year=rights.get("copyright_year"),
            country=str(rights.get("country", "")),
            additional_credits=list(rights.get("additional_credits") or []),
            rights_confirmed=bool(rights.get("rights_confirmed", False)),
        )

    def to_lines(self) -> list[str]:
        """악보 상단에 표시할 라인 목록."""
        lines: list[str] = []
        if self.creator_name:
            lines.append(f"Composer: {self.creator_name}")
        if self.license_type:
            lines.append(f"License: {self.license_type}")
        if self.isrc:
            lines.append(f"ISRC: {self.isrc}")
        if self.copyright_year or self.country:
            year = self.copyright_year or ""
            country = self.country or ""
            lines.append(f"(c) {year} {country}".strip())
        for credit in self.additional_credits:
            role = credit.get("role", "credit")
            name = credit.get("name", "")
            if name:
                lines.append(f"{role.capitalize()}: {name}")
        return lines


def format_attribution_lines(rights: dict[str, Any] | None) -> list[str]:
    """rights dict → 표시용 라인 리스트."""
    return CreatorAttribution.from_tl_rights(rights).to_lines()


def build_metadata(
    *,
    title: str = "",
    artist: str = "",
    rights: dict[str, Any] | None = None,
) -> metadata.Metadata:
    """music21 Metadata 객체 생성 (원칙 6 반영)."""
    md = metadata.Metadata()
    if title:
        md.title = title
    if artist:
        md.alternativeTitle = artist

    attr = CreatorAttribution.from_tl_rights(rights)

    if attr.creator_name:
        md.composer = attr.creator_name

    copy_parts: list[str] = []
    if attr.copyright_year or attr.country:
        copy_parts.append(f"(c) {attr.copyright_year or ''} {attr.country or ''}".strip())
    if attr.isrc:
        copy_parts.append(f"ISRC {attr.isrc}")
    if attr.license_type:
        copy_parts.append(f"License: {attr.license_type}")
    if copy_parts:
        md.copyright = " | ".join(copy_parts)

    if attr.additional_credits:
        credits = ", ".join(
            f"{c.get('role', 'credit')}: {c.get('name', '')}"
            for c in attr.additional_credits
            if c.get("name")
        )
        if credits:
            md.movementName = credits

    return md
