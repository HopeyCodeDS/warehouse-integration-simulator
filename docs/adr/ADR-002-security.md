# ADR-002: Service Autonomy — Duplicate DTOs, Shared Config Conventions

## Status
Accepted

## Context
Multiple services exchange the same conceptual payloads (orders, tasks,
integration events). There are two ways to share these definitions:

1. A shared library (e.g., `packages/common`) imported by every service.
2. Each service owns its own local definitions (DTOs/models) of the data it consumes.

A shared library reduces duplication but couples every service to one artifact:
changing a "shared order model" forces simultaneous redeployment of all
consumers and leaks one context's internal representation into another.
This violates bounded-context isolation and independent deployability -
the two properties this project exists to demonstrate.

Configuration is different from domain data. Database hosts, broker
addresses, and service URLs are deployment concerns, not business concepts.
Duplicating a *convention* for config (same env-var names, same fail-fast
Settings pattern) does not couple business logic.

## Decision
1. Services do NOT share a domain-model library. Each service defines its own
   DTOs (Pydantic schemas / SQLAlchemy models), limited to the fields it needs.
   Example: the Integration Engine defines its own view of `IntegrationEvent`;
   the WMS defines `TaskCreate` independently of the ERP's `OrderCreate`.
2. Cross-context identifiers travel as plain values (`product_sku`,
   `order_number`), never as foreign keys or shared objects.
3. Configuration follows one shared convention instead: every service loads
   settings from environment variables using the same fail-fast `Settings`
   pattern (secrets required, non-secrets defaulted) with unified variable
   names (`POSTGRES_*`, `MQTT_BROKER_*`).

## Consequences
Positive:
- Services stay independently deployable and evolvable.
- Each context can change its internal representation without coordination.
- Operational consistency: one way to configure any service, which simplifies
  commissioning and troubleshooting on site.

Trade-offs:
- Deliberate duplication of DTO definitions; a contract change must be updated
  in each consumer manually.
- Contract drift is possible; mitigated by integration/FAT tests (Week 8–10)
  and the documented API spec (`docs/api-spec.md`).

## Related
- ADR-001 (database isolation and schemas)
- Week 8–10 integration tests act as contract tests between contexts.