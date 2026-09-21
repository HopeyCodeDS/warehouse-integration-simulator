# Factory Acceptance Test (FAT) Runbook
**Objective:** Verify logical correctness of the WIS platform in a controlled environment.

| Test ID | Scenario | Expected Result | Status |
| :--- | :--- | :--- | :--- |
| FAT-01 | Create Order (Valid) | ERP returns 201, WMS allocates stock, Robot moves. | [ ] |
| FAT-02 | Create Order (Insufficient Stock) | WMS returns 409 Conflict, Order remains PENDING. | [ ] |
| FAT-03 | MQTT Broker Offline | Integration Engine logs "Connection Refused", retries. | [ ] |
| FAT-04 | OPC UA Tag Type Mismatch | Gateway logs error, PLC continues running. | [ ] |