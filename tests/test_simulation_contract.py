import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "services" / "robot-simulator"))

from simulation import build_route, legacy_to_world, world_to_legacy


class SimulationContractTests(unittest.TestCase):
    def test_task_route_uses_allocated_rack_and_destination_dock(self):
        route = build_route({"x": 2.5, "z": 3.3}, "Rack-A1", "Dock-3")

        self.assertEqual(route[0], {"x": 2.5, "z": 3.3})
        self.assertEqual(route[2], {"x": -10.0, "z": -5.5})
        self.assertEqual(route[-1], {"x": 11.8, "z": 1.6})

    def test_legacy_coordinates_round_trip(self):
        world_point = {"x": 11.8, "z": 1.6}
        legacy_point = world_to_legacy(world_point)
        normalized = legacy_to_world(legacy_point)

        self.assertAlmostEqual(normalized["x"], world_point["x"], places=1)
        self.assertAlmostEqual(normalized["z"], world_point["z"], places=1)


if __name__ == "__main__":
    unittest.main()
