"""Data model for parsed citations and URL sources."""

from dataclasses import dataclass, field
from enum import Enum


class CitationType(Enum):
    CASE = "case"
    STATUTE = "statute"
    CONSTITUTION = "constitution"
    COURT_RULE = "court_rule"
    REGULATION = "regulation"


@dataclass
class Source:
    name: str
    url: str
    verified: bool | None = None
    anchor: str | None = None


@dataclass
class Citation:
    raw_text: str
    cite_type: CitationType
    jurisdiction: str
    normalized: str
    components: dict = field(default_factory=dict)
    pinpoint: str | None = None
    sources: list[Source] = field(default_factory=list)
    position: int = 0  # character offset in source text
