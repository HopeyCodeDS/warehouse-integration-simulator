import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "traffic-manager"))

from manager import release, reservations, try_reserve


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
