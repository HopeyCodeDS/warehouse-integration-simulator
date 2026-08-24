# ADR-001: Database Isolation and Schemas

## Status
Accepted

## Context
In a real industrial environment, the ERP (e.g., SAP) and WMS are entirely separate systems owned by different teams. They do not share a single database schema. Furthermore, integration layers require strict observability (logging) to troubleshoot OT/IT communication failures.

## Decision
We will use a single PostgreSQL instance for local development convenience, but strictly separate the domains using PostgreSQL Schemas:
- `erp.*` for order and master product data.
- `wms.*` for physical inventory, locations, and equipment configuration.
- `integration.*` for event logging and transaction auditing.

We will avoid cross-schema Foreign Keys between ERP and WMS to simulate Microservice Data Sovereignty.

## Consequences
- The Integration Engine must explicitly transform and route data between schemas.
- Easy migration path: In production, these schemas will simply become separate physical databases.