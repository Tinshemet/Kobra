"""Provisional public contracts for application-independent interpretation.

Offsets count Python Unicode characters, not UTF-8 bytes. Rich READ and RESOLVE
representations remain client-supplied types until their semantic contract is agreed.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


@dataclass(frozen=True)
class Request:
    text: str
    conversation_id: str | None = None


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str


@dataclass(frozen=True)
class TextView:
    original: str
    text: str
    # Each normalized boundary maps to a boundary in the original request.
    back: tuple[int, ...]
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if len(self.back) != len(self.text) + 1:
            raise ValueError("back must contain one entry per text boundary")
        if any(
            type(offset) is not int or not 0 <= offset <= len(self.original)
            for offset in self.back
        ):
            raise ValueError("back contains an invalid original-text offset")
        if any(left > right for left, right in zip(self.back, self.back[1:])):
            raise ValueError("back must be monotonic")
        if self.text != self.original and not self.diagnostics:
            raise ValueError("text changes require a diagnostic")


@dataclass(frozen=True)
class Capability:
    id: str
    description: str


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    revision: str
    vocabulary: tuple[str, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    contract_version: str = "1"

    def __post_init__(self) -> None:
        if self.contract_version != "1":
            raise ValueError("unsupported client contract version")
        if not self.client_id or not self.revision:
            raise ValueError("client_id and revision are required")
        ids = [capability.id for capability in self.capabilities]
        if any(not identity for identity in ids) or len(set(ids)) != len(ids):
            raise ValueError("capability IDs must be nonempty and unique")


class ModelProvider(Protocol):
    def complete(
        self, *, prompt: str, text: str, schema: Mapping[str, object]
    ) -> Mapping[str, object]: ...


class ContextProvider(Protocol):
    def lookup(self, reference: str, *, request: Request) -> tuple[str, ...]:
        """Return candidate identifiers; empty means unresolved, not nonexistent."""
        ...


class RouteStatus(str, Enum):
    READY = "ready"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"
    REFUSED = "refused"


@dataclass(frozen=True)
class RouteDecision:
    status: RouteStatus
    reason: str
    capability_id: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, RouteStatus):
            raise TypeError("status must be a RouteStatus")
        if not self.reason:
            raise ValueError("routing requires a reason")
        if self.status is RouteStatus.READY and not self.capability_id:
            raise ValueError("ready routing requires a capability")
        if self.status is not RouteStatus.READY and self.capability_id is not None:
            raise ValueError("only ready routing may select a capability")


class PolicyProvider(Protocol):
    def evaluate(self, decision: RouteDecision, *, request: Request) -> RouteDecision:
        """Apply application policy; this must not dispatch or execute a tool."""
        ...


@dataclass(frozen=True)
class Services:
    config: ClientConfig
    model: ModelProvider | None = None
    context: ContextProvider | None = None
    policy: PolicyProvider | None = None
