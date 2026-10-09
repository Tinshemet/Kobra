import unittest
from unittest.mock import Mock

from kobra import (
    Capability,
    ClientConfig,
    Diagnostic,
    IdentityFrontDoor,
    Pipeline,
    Request,
    RouteDecision,
    RouteStatus,
    Services,
    TextView,
)


class PipelineTests(unittest.TestCase):
    def make_pipeline(self, policy=None, capability="reminder"):
        services = Services(
            ClientConfig(
                "test", "1", capabilities=(Capability(capability, "Test capability"),)
            ),
            policy=policy,
        )
        reader, resolver, router = Mock(), Mock(), Mock()
        reader.read.return_value = ("reading",)
        resolver.resolve.return_value = ("resolved",)
        router.route.return_value = RouteDecision(
            RouteStatus.READY, "Test route", capability
        )
        return Pipeline(IdentityFrontDoor(), reader, resolver, router, services)

    def test_stage_order_and_intermediate_results_for_two_clients(self):
        for capability, text in (
            ("reminder", "remind me tomorrow"),
            ("vm.stop", "stop alpha"),
        ):
            with self.subTest(capability=capability):
                pipeline = self.make_pipeline(capability=capability)
                calls = Mock()
                calls.attach_mock(pipeline.reader, "reader")
                calls.attach_mock(pipeline.resolver, "resolver")
                calls.attach_mock(pipeline.router, "router")
                request = Request(text)
                result = pipeline.interpret(request)
                self.assertEqual(
                    [call[0] for call in calls.mock_calls],
                    ["reader.read", "resolver.resolve", "router.route"],
                )
                pipeline.resolver.resolve.assert_called_once_with(
                    result.reading, request, pipeline.services
                )
                pipeline.router.route.assert_called_once_with(
                    result.resolved, request, pipeline.services
                )
                self.assertEqual(result.decision.capability_id, capability)
                self.assertEqual(result.view.original, text)

    def test_identity_preserves_unicode_and_empty_text(self):
        for text in ("", "call Zoë 🐍", "שלום"):
            result = self.make_pipeline().interpret(Request(text))
            self.assertEqual(result.view.text, text)
            self.assertEqual(result.view.back, tuple(range(len(text) + 1)))

    def test_policy_decision_keeps_original_route(self):
        policy = Mock()
        policy.evaluate.return_value = RouteDecision(
            RouteStatus.REFUSED, "Client policy"
        )
        result = self.make_pipeline(policy=policy).interpret(Request("anything"))
        self.assertEqual(result.proposed_route.status, RouteStatus.READY)
        self.assertEqual(result.decision.status, RouteStatus.REFUSED)
        policy.evaluate.assert_called_once_with(
            result.proposed_route, request=result.request
        )

    def test_reader_failure_stops_later_stages(self):
        pipeline = self.make_pipeline()
        pipeline.reader.read.side_effect = RuntimeError("provider failed")
        with self.assertRaisesRegex(RuntimeError, "provider failed"):
            pipeline.interpret(Request("anything"))
        pipeline.resolver.resolve.assert_not_called()
        pipeline.router.route.assert_not_called()

    def test_undeclared_capability_rejected_from_router_or_policy(self):
        bad = RouteDecision(RouteStatus.READY, "Unknown capability", "missing")
        pipeline = self.make_pipeline()
        pipeline.router.route.return_value = bad
        with self.assertRaisesRegex(ValueError, "undeclared"):
            pipeline.interpret(Request("anything"))
        policy = Mock()
        policy.evaluate.return_value = bad
        with self.assertRaisesRegex(ValueError, "undeclared"):
            self.make_pipeline(policy).interpret(Request("anything"))

    def test_original_request_cannot_be_replaced(self):
        pipeline = self.make_pipeline()
        front = Mock()
        front.normalize.return_value = TextView(
            "different", "different", tuple(range(10))
        )
        pipeline = Pipeline(
            front,
            pipeline.reader,
            pipeline.resolver,
            pipeline.router,
            pipeline.services,
        )
        with self.assertRaisesRegex(ValueError, "original request"):
            pipeline.interpret(Request("anything"))
        pipeline.reader.read.assert_not_called()


class ContractTests(unittest.TestCase):
    def test_invalid_maps_and_silent_changes_rejected(self):
        for back in ((0,), (0, 4), (1, 0), (0, True)):
            with self.subTest(back=back), self.assertRaises(ValueError):
                TextView("x", "x", back)
        with self.assertRaisesRegex(ValueError, "diagnostic"):
            TextView("X", "x", (0, 1))
        TextView("X", "x", (0, 1), (Diagnostic("case", "Lowercased"),))

    def test_invalid_client_contracts_rejected(self):
        with self.assertRaises(ValueError):
            ClientConfig("test", "1", contract_version="2")
        with self.assertRaises(ValueError):
            ClientConfig(
                "test", "1", capabilities=(Capability("x", ""), Capability("x", ""))
            )

    def test_route_requires_reason_and_consistent_destination(self):
        for args in (
            (RouteStatus.READY, "why"),
            (RouteStatus.REFUSED, "why", "x"),
            (RouteStatus.UNSUPPORTED, ""),
            ("ready", "why", "x"),
        ):
            with self.subTest(args=args), self.assertRaises((TypeError, ValueError)):
                RouteDecision(*args)


if __name__ == "__main__":
    unittest.main()
