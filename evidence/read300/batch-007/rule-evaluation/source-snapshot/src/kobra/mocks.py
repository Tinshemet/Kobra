"""Explicit pipeline test doubles. These do not reason or authorize execution."""

from .contracts import Diagnostic, RouteDecision, RouteStatus


class MockResolver:
    def resolve(self, reading, request, services):
        return reading


class MockRouter:
    def route(self, resolved, request, services):
        return RouteDecision(
            RouteStatus.UNSUPPORTED,
            "Mock ROUTE reached; security evaluation and execution are not implemented.",
            diagnostics=(Diagnostic("route.mock", "Pipeline plumbing only."),),
        )
