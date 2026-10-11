"""Stage coordination only. No default parser, model, storage, or executor."""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from .contracts import Request, RouteDecision, Services, TextView

ReadingT = TypeVar("ReadingT")
ResolvedT = TypeVar("ResolvedT")
ReadingOut_co = TypeVar("ReadingOut_co", covariant=True)
ReadingIn_contra = TypeVar("ReadingIn_contra", contravariant=True)
ResolvedOut_co = TypeVar("ResolvedOut_co", covariant=True)
ResolvedIn_contra = TypeVar("ResolvedIn_contra", contravariant=True)


class FrontDoor(Protocol):
    def normalize(self, request: Request, services: Services) -> TextView: ...


class Reader(Protocol[ReadingOut_co]):
    def read(
        self, view: TextView, request: Request, services: Services
    ) -> ReadingOut_co: ...


class Resolver(Protocol[ReadingIn_contra, ResolvedOut_co]):
    def resolve(
        self, reading: ReadingIn_contra, request: Request, services: Services
    ) -> ResolvedOut_co: ...


class Router(Protocol[ResolvedIn_contra]):
    def route(
        self, resolved: ResolvedIn_contra, request: Request, services: Services
    ) -> RouteDecision: ...


class IdentityFrontDoor:
    """Preserve input exactly; linguistic normalization is not implemented yet."""

    def normalize(self, request: Request, services: Services) -> TextView:
        return TextView(request.text, request.text, tuple(range(len(request.text) + 1)))


@dataclass(frozen=True)
class Interpretation(Generic[ReadingT, ResolvedT]):
    request: Request
    view: TextView
    reading: ReadingT
    resolved: ResolvedT
    proposed_route: RouteDecision
    decision: RouteDecision


@dataclass(frozen=True)
class Pipeline(Generic[ReadingT, ResolvedT]):
    front_door: FrontDoor
    reader: Reader[ReadingT]
    resolver: Resolver[ReadingT, ResolvedT]
    router: Router[ResolvedT]
    services: Services

    def interpret(self, request: Request) -> Interpretation[ReadingT, ResolvedT]:
        view = self.front_door.normalize(request, self.services)
        if view.original != request.text:
            raise ValueError("front door lost the original request")
        reading = self.reader.read(view, request, self.services)
        resolved = self.resolver.resolve(reading, request, self.services)
        proposed = self.router.route(resolved, request, self.services)
        self._validate_route(proposed)
        decision = proposed
        if self.services.policy is not None:
            decision = self.services.policy.evaluate(proposed, request=request)
            self._validate_route(decision)
        return Interpretation(request, view, reading, resolved, proposed, decision)

    def _validate_route(self, decision: RouteDecision) -> None:
        if not isinstance(decision, RouteDecision):
            raise TypeError("router and policy must return RouteDecision")
        if decision.capability_id is not None and decision.capability_id not in {
            capability.id for capability in self.services.config.capabilities
        }:
            raise ValueError("route selected an undeclared capability")
