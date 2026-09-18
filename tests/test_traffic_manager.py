import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "traffic_manager_service", Path(__file__).parents[1] / "services" / "traffic-manager" / "manager.py"
)
traffic_manager_service = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(traffic_manager_service)
release = traffic_manager_service.release
reservations = traffic_manager_service.reservations
try_reserve = traffic_manager_service.try_reserve


class TrafficReservationTests(unittest.TestCase):
    def setUp(self):
        reservations.clear()

    def test_conflicting_routes_are_not_granted(self):
        route = [{"x": 0, "z": 0}, {"x": 1, "z": 0}, {"x": 2, "z": 0}]
        self.assertEqual(try_reserve("AMR-A", route, "req-a"), (True, None))
        granted, conflict = try_reserve("AMR-B", route, "req-b")
        self.assertFalse(granted)
        self.assertEqual(conflict, "AMR-A")

    def test_release_allows_the_next_robot(self):
        route = [{"x": 0, "z": 0}, {"x": 1, "z": 0}]
        try_reserve("AMR-A", route, "req-a")
        release("AMR-A", route)
        self.assertEqual(try_reserve("AMR-B", route, "req-b"), (True, None))

    def test_reverse_edges_share_the_same_safety_reservation(self):
        forward = [{"x": 0, "z": 0}, {"x": 1, "z": 0}]
        reverse = [{"x": 1, "z": 0}, {"x": 0, "z": 0}]
        self.assertEqual(try_reserve("AMR-A", forward, "req-a"), (True, None))
        granted, conflict = try_reserve("AMR-B", reverse, "req-b")
        self.assertFalse(granted)
        self.assertEqual(conflict, "AMR-A")


if __name__ == "__main__":
    unittest.main()
