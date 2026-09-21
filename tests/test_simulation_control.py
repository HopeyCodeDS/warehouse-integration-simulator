import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_spec = importlib.util.spec_from_file_location(
    "simulation_control_service", Path(__file__).parents[1] / "services" / "simulation-control" / "manager.py"
)
manager = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manager)


class SimulationControlTests(unittest.TestCase):
    def setUp(self):
        manager.state.update({"status": "RUNNING", "speed": 1.0, "tick": 0, "scenario": "default"})

    def test_handle_command_matches_paho_v2_callback_signature(self):
        client = MagicMock()
        message = MagicMock()
        message.payload = b'{"command": "pause"}'
        manager.handle_command(client, None, message)
        self.assertEqual(manager.state["status"], "PAUSED")

    def test_pause_then_resume_round_trip(self):
        client = MagicMock()
        pause_message = MagicMock(payload=b'{"command": "pause"}')
        resume_message = MagicMock(payload=b'{"command": "resume"}')
        manager.handle_command(client, None, pause_message)
        self.assertEqual(manager.state["status"], "PAUSED")
        manager.handle_command(client, None, resume_message)
        self.assertEqual(manager.state["status"], "RUNNING")

    def test_step_advances_exactly_one_tick_while_paused(self):
        client = MagicMock()
        step_message = MagicMock(payload=b'{"command": "step"}')
        manager.handle_command(client, None, step_message)
        self.assertEqual(manager.state["status"], "PAUSED")
        self.assertEqual(manager.state["tick"], 1)
        manager.handle_command(client, None, step_message)
        self.assertEqual(manager.state["tick"], 2)

    def test_speed_command_is_clamped_to_a_safe_range(self):
        client = MagicMock()
        message = MagicMock(payload=b'{"command": "speed", "value": 99}')
        manager.handle_command(client, None, message)
        self.assertEqual(manager.state["speed"], 8.0)

    def test_invalid_payload_does_not_raise(self):
        client = MagicMock()
        message = MagicMock(payload=b'not-json')
        manager.handle_command(client, None, message)


if __name__ == "__main__":
    unittest.main()
