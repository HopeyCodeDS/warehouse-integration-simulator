import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from support import FakeSession, Row, load_app_package, stub_db_env, stub_mqtt

stub_db_env()
stub_mqtt()
wms = load_app_package("wms_app", "wms-api")

from fastapi import HTTPException

allocate = wms.allocate
ItemLine = wms.ItemLine
Inventory = wms.Inventory
Location = wms.Location

RACK_A1 = uuid.uuid4()
RACK_B2 = uuid.uuid4()


def session_with(inventory, locations=()):
    return FakeSession().seed(Inventory, inventory).seed(Location, locations)


class AllocationTests(unittest.TestCase):
    def test_allocates_a_line_against_sufficient_stock(self):
        db = session_with(
            [Row(product_sku="P100", quantity=10, location_id=RACK_A1)],
            [Row(id=RACK_A1, name="Rack-A1")],
        )

        self.assertEqual(
            allocate([ItemLine(sku="P100", qty=4)], db),
            [{
                "sku": "P100",
                "qty": 4,
                "location_id": str(RACK_A1),
                "source_location": "Rack-A1",
            }],
        )

    def test_rejects_when_stock_is_short(self):
        db = session_with([Row(product_sku="P100", quantity=2, location_id=RACK_A1)])

        with self.assertRaises(HTTPException) as raised:
            allocate([ItemLine(sku="P100", qty=5)], db)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("P100", raised.exception.detail)

    def test_rejects_an_unknown_sku(self):
        db = session_with([Row(product_sku="P100", quantity=10, location_id=RACK_A1)])

        with self.assertRaises(HTTPException) as raised:
            allocate([ItemLine(sku="P999", qty=1)], db)

        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("P999", raised.exception.detail)

    def test_exact_stock_is_enough(self):
        db = session_with(
            [Row(product_sku="P100", quantity=3, location_id=RACK_A1)],
            [Row(id=RACK_A1, name="Rack-A1")],
        )

        self.assertEqual(allocate([ItemLine(sku="P100", qty=3)], db)[0]["qty"], 3)

    def test_skips_a_location_that_cannot_cover_the_whole_line(self):
        db = session_with(
            [
                Row(product_sku="P100", quantity=1, location_id=RACK_A1),
                Row(product_sku="P100", quantity=9, location_id=RACK_B2),
            ],
            [Row(id=RACK_A1, name="Rack-A1"), Row(id=RACK_B2, name="Rack-B2")],
        )

        allocation = allocate([ItemLine(sku="P100", qty=5)], db)[0]

        self.assertEqual(allocation["source_location"], "Rack-B2")
        self.assertEqual(allocation["location_id"], str(RACK_B2))

    def test_allocates_every_line_in_request_order(self):
        db = session_with(
            [
                Row(product_sku="P100", quantity=10, location_id=RACK_A1),
                Row(product_sku="P200", quantity=10, location_id=RACK_B2),
            ],
            [Row(id=RACK_A1, name="Rack-A1"), Row(id=RACK_B2, name="Rack-B2")],
        )

        allocations = allocate(
            [ItemLine(sku="P200", qty=1), ItemLine(sku="P100", qty=2)], db
        )

        self.assertEqual([a["sku"] for a in allocations], ["P200", "P100"])
        self.assertEqual([a["source_location"] for a in allocations], ["Rack-B2", "Rack-A1"])

    def test_rejects_the_whole_request_when_a_later_line_is_short(self):
        db = session_with(
            [
                Row(product_sku="P100", quantity=10, location_id=RACK_A1),
                Row(product_sku="P200", quantity=1, location_id=RACK_B2),
            ],
            [Row(id=RACK_A1, name="Rack-A1"), Row(id=RACK_B2, name="Rack-B2")],
        )

        with self.assertRaises(HTTPException) as raised:
            allocate([ItemLine(sku="P100", qty=2), ItemLine(sku="P200", qty=5)], db)

        self.assertIn("P200", raised.exception.detail)

    def test_reports_unknown_when_the_location_row_is_missing(self):
        db = session_with([Row(product_sku="P100", quantity=10, location_id=RACK_A1)])

        self.assertEqual(
            allocate([ItemLine(sku="P100", qty=1)], db)[0]["source_location"], "Unknown"
        )

    def test_allocating_nothing_yields_no_allocations(self):
        self.assertEqual(allocate([], session_with([])), [])


if __name__ == "__main__":
    unittest.main()
