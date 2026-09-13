import json
import os
import time
import unittest
import urllib.error
import urllib.request
from uuid import uuid4


ERP_API_URL = os.getenv("ERP_API_URL", "http://localhost:8000")
POLL_INTERVAL_SECONDS = 2
FLOW_TIMEOUT_SECONDS = int(os.getenv("E2E_TIMEOUT_SECONDS", "90"))


def request_json(method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{ERP_API_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


class OrderFlowE2ETests(unittest.TestCase):
    def test_order_is_completed_by_the_full_integration_flow(self):
        order_number = f"ORD-E2E-{uuid4().hex[:12].upper()}"
        payload = {
            "order_number": order_number,
            "customer": "E2E Test Customer",
            "destination_dock": "Dock-3",
            "items": [{"product_sku": "P100", "requested_qty": 1}],
        }

        status_code, created_order = request_json("POST", "/api/orders", payload)

        self.assertEqual(status_code, 201)
        self.assertEqual(created_order["order_number"], order_number)
        self.assertEqual(created_order["status"], "PENDING")

        deadline = time.monotonic() + FLOW_TIMEOUT_SECONDS
        observed_statuses = []
        while time.monotonic() < deadline:
            _, order = request_json("GET", f"/api/orders/{order_number}")
            observed_statuses.append(order["status"])
            if order["status"] == "COMPLETED":
                return
            time.sleep(POLL_INTERVAL_SECONDS)

        self.fail(
            f"Order {order_number} did not complete within "
            f"{FLOW_TIMEOUT_SECONDS}s; observed statuses: {observed_statuses}"
        )

    def test_order_creation_rejects_invalid_quantity(self):
        payload = {
            "order_number": f"ORD-E2E-INVALID-{uuid4().hex[:8].upper()}",
            "customer": "E2E Test Customer",
            "destination_dock": "Dock-3",
            "items": [{"product_sku": "P100", "requested_qty": 0}],
        }

        with self.assertRaises(urllib.error.HTTPError) as error:
            request_json("POST", "/api/orders", payload)

        self.assertEqual(error.exception.code, 422)


if __name__ == "__main__":
    unittest.main()