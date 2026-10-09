"""Exact-match wiring fixture, not a parser. Run after installing Kobra."""

from kobra import (
    Capability,
    ClientConfig,
    IdentityFrontDoor,
    Pipeline,
    Request,
    RouteDecision,
    RouteStatus,
    Services,
)


class FixtureReader:
    def read(self, view, request, services):
        return view.text == "remind me tomorrow"


class FixtureResolver:
    def resolve(self, reading, request, services):
        return reading


class FixtureRouter:
    def route(self, resolved, request, services):
        if resolved:
            return RouteDecision(
                RouteStatus.READY, "Matched demonstration fixture", "reminder"
            )
        return RouteDecision(RouteStatus.UNSUPPORTED, "Outside this fixture's scope")


def build_pipeline():
    return Pipeline(
        front_door=IdentityFrontDoor(),
        reader=FixtureReader(),
        resolver=FixtureResolver(),
        router=FixtureRouter(),
        services=Services(
            ClientConfig(
                client_id="assistant-demo",
                revision="1",
                capabilities=(Capability("reminder", "Receive a reminder request"),),
            )
        ),
    )


if __name__ == "__main__":
    print(build_pipeline().interpret(Request("remind me tomorrow")).decision)
