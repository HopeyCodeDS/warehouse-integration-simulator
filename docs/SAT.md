# Site Acceptance Test (SAT) Runbook
**Objective:** Verify system resilience and recovery in a live environment.

| Test ID | Scenario | Action | Expected Result |
| :--- | :--- | :--- | :--- |
| SAT-01 | PLC Disconnect | `docker stop wis-opcua-plc` | Commissioning UI shows "OPC UA: OFFLINE". |
| SAT-02 | Network Partition | Block MQTT port | Robot stops receiving tasks, logs error. |
| SAT-03 | Recovery | `docker start wis-opcua-plc` | Commissioning UI turns Green automatically. |