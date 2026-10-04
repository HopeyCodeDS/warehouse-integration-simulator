# Factory Acceptance Test (FAT) Runbook
**Objective:** Verify logical correctness of the WIS platform in a controlled environment.

| Test ID | Scenario | Expected Result | Status | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| FAT-01 | Create Order (Valid) | ERP returns 201, WMS allocates stock, Robot moves. | [x] | 2026-10-02, `make e2e`. `ORD-E2E-44D234CC5347` reached `COMPLETED`; one correlation ID across `ORDER_CREATED` -> `TASK_DISPATCHED` -> `ORDER_COMPLETED`, all `PROCESSED`. |
| FAT-02 | Create Order (Insufficient Stock) | WMS returns 409 Conflict, Order remains PENDING. | [ ] | Allocation rules covered by unit tests in [tests/test_wms_allocation.py](../tests/test_wms_allocation.py), but not yet executed as a live FAT run. |
| FAT-03 | MQTT Broker Offline | Integration Engine logs "Connection Refused", retries. | [ ] | Not executed. |
| FAT-04 | OPC UA Tag Type Mismatch | Gateway logs error, PLC continues running. | [ ] | Not executed. |

**Preconditions.** Run against a volume created from the current `database/*.sql`. Postgres only applies init scripts to an empty data directory, so a volume predating a schema change will fail in ways unrelated to the scenario under test. Reset with `docker compose down -v` before a clean FAT run.