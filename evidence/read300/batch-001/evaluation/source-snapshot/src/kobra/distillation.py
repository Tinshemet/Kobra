"""Draft READ output contract: prose with mechanically checked references.

Validation establishes structural integrity, never semantic faithfulness.
Source IDs identify supplied input; they do not confer trust or authority.
"""

from dataclasses import dataclass

CONTRACT_VERSION = "distillation-draft-1"


def _nonempty(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _tuple_of(value: tuple, item_type: type, field: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(x, item_type) for x in value):
        raise TypeError(f"{field} must be a tuple of {item_type.__name__}")


@dataclass(frozen=True)
class Source:
    id: str
    text: str

    def __post_init__(self) -> None:
        _nonempty(self.id, "source ID")
        if not isinstance(self.text, str):
            raise TypeError("source text must be a string")


@dataclass(frozen=True)
class SourceSpan:
    source_id: str
    start: int
    end: int

    def __post_init__(self) -> None:
        _nonempty(self.source_id, "source ID")
        if type(self.start) is not int or type(self.end) is not int:
            raise TypeError("offsets must be integers")
        if not 0 <= self.start < self.end:
            raise ValueError("source spans must be nonempty half-open intervals")


@dataclass(frozen=True)
class PointLink:
    target_id: str
    relationship: str

    def __post_init__(self) -> None:
        _nonempty(self.target_id, "link target")
        _nonempty(self.relationship, "relationship")


@dataclass(frozen=True)
class Point:
    id: str
    sentence: str
    evidence: tuple[SourceSpan, ...]
    links: tuple[PointLink, ...] = ()
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _nonempty(self.id, "point ID")
        _nonempty(self.sentence, "point sentence")
        _tuple_of(self.evidence, SourceSpan, "evidence")
        _tuple_of(self.links, PointLink, "links")
        _tuple_of(self.uncertainty, str, "uncertainty")
        if not self.evidence:
            raise ValueError("every point requires source evidence")
        for uncertainty in self.uncertainty:
            _nonempty(uncertainty, "uncertainty")


@dataclass(frozen=True)
class Distillation:
    sources: tuple[Source, ...]
    points: tuple[Point, ...]
    contract_version: str = CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported distillation contract")
        _tuple_of(self.sources, Source, "sources")
        _tuple_of(self.points, Point, "points")
        sources = {source.id: source for source in self.sources}
        point_ids = {point.id for point in self.points}
        if len(sources) != len(self.sources) or len(point_ids) != len(self.points):
            raise ValueError(
                "source IDs and point IDs must be unique within their namespace"
            )
        for point in self.points:
            for span in point.evidence:
                if span.source_id not in sources:
                    raise ValueError("evidence references an unknown source")
                if span.end > len(sources[span.source_id].text):
                    raise ValueError("evidence extends past the source")
            for link in point.links:
                if link.target_id not in point_ids or link.target_id == point.id:
                    raise ValueError(
                        "point links must reference another existing point"
                    )
