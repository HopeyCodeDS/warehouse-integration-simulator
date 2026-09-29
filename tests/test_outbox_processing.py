import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))

from support import FakeSession, load_module, silence_stdout, stub_db_env, stub_mqtt

stub_db_env()
stub_mqtt()
worker = load_module("integration_engine_worker", "integration-engine/worker.py")

IntegrationEvent = worker.IntegrationEvent

ORDER_PAYLOAD = {
    "correlation_id": "corr-123",
    "order_number": "ORD-001",
    "customer": "Acme Manufacturing",
    "destination_dock": "Dock-3",
    "items": [{"sku": "P100", "qty": 2}],
}


def http_response(status_code, body=None, text=""):
    response = Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = body if body is not None else {}
    response.text = text
    return response


def pending_order(payload=None):
    return IntegrationEvent(
        source="ERP",
        destination="Integration_Engine",
        event_type="ORDER_CREATED",
        correlation_id=ORDER_PAYLOAD["correlation_id"],
        payload=ORDER_PAYLOAD if payload is None else payload,
        status="PENDING",
    )


def added_event(db, event_type):
    matches = [e for e in db.added if e.event_type == event_type]
    assert len(matches) == 1, f"expected exactly one {event_type}, got {len(matches)}"
    return matches[0]


class DispatchTests(unittest.TestCase):
    def setUp(self):
        silence_stdout(self)

    def test_forwards_the_order_to_the_wms(self):
        db, event = FakeSession(), pending_order()

        with patch.object(worker.requests, "post", return_value=http_response(201, {"task_id": "T-1"})) as post:
            worker.process_order_created(event, db)

        self.assertEqual(post.call_args.args[0], worker.settings.WMS_API_URL)
        self.assertEqual(post.call_args.kwargs["json"], {
            "order_number": "ORD-001",
            "task_type": "PICK_AND_MOVE",
            "correlation_id": "corr-123",
            "items": [{"sku": "P100", "qty": 2}],
            "payload": {"customer": "Acme Manufacturing", "destination_dock": "Dock-3"},
        })

    def test_marks_the_outbox_row_processed_on_success(self):
        db, event = FakeSession(), pending_order()

        with patch.object(worker.requests, "post", return_value=http_response(201, {"task_id": "T-1"})):
            worker.process_order_created(event, db)

        self.assertEqual(event.status, "PROCESSED")

    def test_records_a_dispatch_audit_event_carrying_the_correlation_id(self):
        db, event = FakeSession(), pending_order()

        with patch.object(worker.requests, "post", return_value=http_response(201, {"task_id": "T-1"})):
            worker.process_order_created(event, db)

        audit = added_event(db, "TASK_DISPATCHED")
        self.assertEqual(audit.correlation_id, "corr-123")
        self.assertEqual(audit.status, "PROCESSED")
        self.assertEqual(audit.payload["task_id"], "T-1")

    def test_marks_the_outbox_row_failed_when_the_wms_rejects(self):
        db, event = FakeSession(), pending_order()

        with patch.object(worker.requests, "post", return_value=http_response(409, {"detail": "Insufficient stock for P100"})):
            worker.process_order_created(event, db)

        self.assertEqual(event.status, "FAILED")

    def test_records_a_rejection_audit_event(self):
        db, event = FakeSession(), pending_order()

        with patch.object(worker.requests, "post", return_value=http_response(409, {"detail": "Insufficient stock for P100"})):
            worker.process_order_created(event, db)

        audit = added_event(db, "TASK_REJECTED")
        self.assertEqual(audit.status, "FAILED")
        self.assertEqual(audit.correlation_id, "corr-123")

    def test_accepts_a_json_encoded_payload(self):
        # The ERP writes its outbox payload with json.dumps.
        db, event = FakeSession(), pending_order(json.dumps(ORDER_PAYLOAD))

        with patch.object(worker.requests, "post", return_value=http_response(201, {"task_id": "T-1"})) as post:
            worker.process_order_created(event, db)

        self.assertEqual(post.call_args.kwargs["json"]["correlation_id"], "corr-123")
        self.assertEqual(event.status, "PROCESSED")


class CompletionTests(unittest.TestCase):
    def setUp(self):
        silence_stdout(self)

    def test_patches_the_order_status_in_the_erp(self):
        db = FakeSession()

        with patch.object(worker.requests, "patch", return_value=http_response(200)) as request:
            worker.process_order_completed({"order_number": "ORD-001", "correlation_id": "corr-123"}, db)

        self.assertEqual(request.call_args.args[0], f"{worker.settings.ERP_API_URL}/ORD-001/status")
        self.assertEqual(request.call_args.kwargs["json"], {"status": "COMPLETED"})

    def test_records_the_completion_against_the_correlation_id(self):
        db = FakeSession()

        with patch.object(worker.requests, "patch", return_value=http_response(200)):
            worker.process_order_completed({"order_number": "ORD-001", "correlation_id": "corr-123"}, db)

        audit = added_event(db, "ORDER_COMPLETED")
        self.assertEqual(audit.correlation_id, "corr-123")
        self.assertEqual(audit.status, "PROCESSED")

    def test_records_a_failure_when_the_erp_rejects_the_patch(self):
        db = FakeSession()

        with patch.object(worker.requests, "patch", return_value=http_response(500)):
            worker.process_order_completed({"order_number": "ORD-001", "correlation_id": "corr-123"}, db)

        self.assertEqual(added_event(db, "ORDER_COMPLETED").status, "FAILED")


class RunLoopTests(unittest.TestCase):
    def setUp(self):
        silence_stdout(self)
        self.drain_completions()

    def tearDown(self):
        self.drain_completions()

    @staticmethod
    def drain_completions():
        while not worker.completion_queue.empty():
            worker.completion_queue.get()

    def run_loop_with(self, db):
        with patch.object(worker, "SessionLocal", return_value=db):
            worker.run_loop()

    def test_only_order_created_events_are_dispatched(self):
        order = pending_order()
        unrelated = IntegrationEvent(
            source="Integration_Engine",
            destination="WMS",
            event_type="TASK_DISPATCHED",
            status="PENDING",
            payload={},
        )
        db = FakeSession().seed(IntegrationEvent, [order, unrelated])

        with patch.object(worker.requests, "post", return_value=http_response(201, {"task_id": "T-1"})) as post:
            self.run_loop_with(db)

        self.assertEqual(post.call_count, 1)
        self.assertEqual(order.status, "PROCESSED")
        self.assertEqual(unrelated.status, "PENDING")

    def test_a_failing_dispatch_is_marked_and_does_not_stop_the_loop(self):
        order = pending_order()
        db = FakeSession().seed(IntegrationEvent, [order])

        with patch.object(worker.requests, "post", side_effect=RuntimeError("wms unreachable")):
            self.run_loop_with(db)

        self.assertEqual(order.status, "ERROR")

    def test_a_malformed_completion_message_does_not_kill_the_worker(self):
        db = FakeSession().seed(IntegrationEvent, [])
        worker.completion_queue.put({"correlation_id": "corr-123"})  # no order_number

        with patch.object(worker.requests, "patch", return_value=http_response(200)):
            self.run_loop_with(db)

        self.assertEqual(db.rollbacks, 1)
        self.assertTrue(db.closed)

    def test_a_bad_completion_does_not_block_the_next_one(self):
        db = FakeSession().seed(IntegrationEvent, [])
        worker.completion_queue.put({"correlation_id": "corr-123"})  # no order_number
        worker.completion_queue.put({"order_number": "ORD-002", "correlation_id": "corr-456"})

        with patch.object(worker.requests, "patch", return_value=http_response(200)) as request:
            self.run_loop_with(db)

        self.assertEqual(request.call_count, 1)
        self.assertEqual(added_event(db, "ORDER_COMPLETED").correlation_id, "corr-456")

    def test_the_session_is_always_closed(self):
        db = FakeSession().seed(IntegrationEvent, [])

        self.run_loop_with(db)

        self.assertTrue(db.closed)


if __name__ == "__main__":
    unittest.main()
