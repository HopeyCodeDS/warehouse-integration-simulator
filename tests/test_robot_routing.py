import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "robot-simulator"))

from simulation import (
    DOCK_POSITIONS,
    HOME_POSITIONS,
    RACK_POSITIONS,
    TRANSFER_POINTS,
    build_route,
    task_route,
)

HOME = {"x": 2.5, "z": 3.3}

# Waypoint slots produced by build_route, in order.
START, RACK, TRANSFER, DOCK_APPROACH, DOCK = 0, 2, 4, 5, 6


class BuildRouteTests(unittest.TestCase):
    def test_route_has_seven_waypoints(self):
        self.assertEqual(len(build_route(HOME, "Rack-A1", "Dock-3")), 7)

    def test_route_starts_at_the_robots_home(self):
        self.assertEqual(build_route(HOME, "Rack-A1", "Dock-3")[START], HOME)

    def test_route_ends_at_the_requested_dock(self):
        route = build_route(HOME, "Rack-A1", "Dock-1")

        self.assertEqual(route[DOCK], DOCK_POSITIONS["Dock-1"])

    def test_route_visits_the_allocated_rack(self):
        route = build_route(HOME, "Rack-B2", "Dock-3")

        self.assertEqual(route[RACK], RACK_POSITIONS["Rack-B2"])

    def test_route_passes_through_the_sort_transfer_point(self):
        route = build_route(HOME, "Rack-A1", "Dock-3")

        self.assertEqual(route[TRANSFER], TRANSFER_POINTS["Sort"])

    def test_leaves_home_along_the_current_row_before_turning(self):
        route = build_route(HOME, "Rack-A1", "Dock-3")

        self.assertEqual(route[1], {"x": RACK_POSITIONS["Rack-A1"]["x"], "z": HOME["z"]})

    def test_approaches_the_dock_from_two_metres_out(self):
        route = build_route(HOME, "Rack-A1", "Dock-1")

        self.assertAlmostEqual(
            route[DOCK_APPROACH]["x"], DOCK_POSITIONS["Dock-1"]["x"] - 2.0, places=6
        )
        self.assertEqual(route[DOCK_APPROACH]["z"], DOCK_POSITIONS["Dock-1"]["z"])

    def test_an_unknown_rack_falls_back_to_the_inbound_transfer_point(self):
        route = build_route(HOME, "Rack-Does-Not-Exist", "Dock-3")

        self.assertEqual(route[RACK], TRANSFER_POINTS["Inbound"])

    def test_a_missing_rack_falls_back_to_the_inbound_transfer_point(self):
        self.assertEqual(build_route(HOME, None, "Dock-3")[RACK], TRANSFER_POINTS["Inbound"])

    def test_an_unknown_dock_falls_back_to_dock_3(self):
        route = build_route(HOME, "Rack-A1", "Dock-Does-Not-Exist")

        self.assertEqual(route[DOCK], DOCK_POSITIONS["Dock-3"])

    def test_a_missing_dock_falls_back_to_dock_3(self):
        self.assertEqual(build_route(HOME, "Rack-A1", None)[DOCK], DOCK_POSITIONS["Dock-3"])

    def test_home_coordinates_are_rounded_to_three_places(self):
        route = build_route({"x": 2.5554, "z": 3.3336}, "Rack-A1", "Dock-3")

        self.assertEqual(route[START], {"x": 2.555, "z": 3.334})


class TaskRouteTests(unittest.TestCase):
    def test_uses_the_source_location_of_the_first_allocation(self):
        task = {"payload": {"allocations": [{"source_location": "Rack-C1"}]}}

        route = task_route(task, "AMR-Ultra")

        self.assertEqual(route[RACK], RACK_POSITIONS["Rack-C1"])

    def test_ignores_later_allocations_when_choosing_the_rack(self):
        task = {"payload": {"allocations": [
            {"source_location": "Rack-C1"},
            {"source_location": "Rack-D1"},
        ]}}

        self.assertEqual(task_route(task, "AMR-Ultra")[RACK], RACK_POSITIONS["Rack-C1"])

    def test_falls_back_to_the_payload_source_location_without_allocations(self):
        task = {"payload": {"source_location": "Rack-E2"}}

        self.assertEqual(task_route(task, "AMR-Ultra")[RACK], RACK_POSITIONS["Rack-E2"])

    def test_payload_dock_wins_over_the_task_level_dock(self):
        task = {"destination_dock": "Dock-1", "payload": {"destination_dock": "Dock-4"}}

        self.assertEqual(task_route(task, "AMR-Ultra")[DOCK], DOCK_POSITIONS["Dock-4"])

    def test_uses_the_task_level_dock_when_the_payload_has_none(self):
        task = {"destination_dock": "Dock-2", "payload": {}}

        self.assertEqual(task_route(task, "AMR-Ultra")[DOCK], DOCK_POSITIONS["Dock-2"])

    def test_defaults_to_dock_3_when_no_dock_is_given(self):
        self.assertEqual(task_route({}, "AMR-Ultra")[DOCK], DOCK_POSITIONS["Dock-3"])

    def test_starts_from_the_named_robots_own_home(self):
        self.assertEqual(task_route({}, "AMR-Vega")[START], HOME_POSITIONS["AMR-Vega"])

    def test_an_unknown_robot_starts_from_the_default_home(self):
        self.assertEqual(
            task_route({}, "AMR-Unregistered")[START], HOME_POSITIONS["AMR-Ultra"]
        )

    def test_a_task_without_a_payload_still_produces_a_route(self):
        self.assertEqual(len(task_route({}, "AMR-Nova")), 7)


if __name__ == "__main__":
    unittest.main()
