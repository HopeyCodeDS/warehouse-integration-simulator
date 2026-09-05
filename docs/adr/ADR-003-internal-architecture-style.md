# ADR-003: Internal Service Architecture - Transaction Scripts Now, Ports & Adapters Where Orchestration Earns It

## Status
Accepted

## Context
Two dominant styles exist for service internals:

1. **Transaction Scripts** (Fowler): each endpoint or worker runs a
   procedural script against the database via an ORM; models are anemic
   data bags; logic lives in handlers.
2. **Hexagonal / Ports & Adapters** (with tactical DDD): a framework-free
   domain core owns behavior; abstract ports define persistence and
   publishing; adapters (SQLAlchemy, MQTT, HTTP) live at the edges and
   dependencies point strictly inward.

Hexagonal buys infrastructure-free unit tests and swappable adapters, at
the cost of 3–4× more files and indirection per service.

WIS contexts are not equally complex:
- ERP and WMS are mostly CRUD plus a small number of explicit business
  rules (validation, stock allocation).
- The Integration Engine is pure orchestration: poll, translate, route,
  retry, log. Its value IS the logic, not the I/O.

Applying one style uniformly to both kinds would either over-engineer
the CRUD services or under-protect the orchestration logic.

## Decision
1. CRUD-heavy contexts (ERP API, WMS API) use **transaction scripts**
   with anemic SQLAlchemy models and Pydantic DTOs at the HTTP boundary.
2. Business rules that exist are written as **small, framework-free
   functions** inside the service (e.g., `allocate()` in the WMS), so
   they remain unit-testable without Docker, even in script style.
   Known deviation: `allocate()` currently raises `HTTPException` for
   brevity; the target convention is domain-level exceptions mapped to
   HTTP status codes at the router.
3. No shared domain library across services (see ADR-002).
4. The Integration Engine is the **first refactor candidate** for
   ports & adapters: `domain/` (translation rules, retry policy),
   `ports/` (OutboxReader, TaskDispatcher, EventPublisher),
   `adapters/` (Postgres, WMS HTTP client, MQTT).
5. Refactor trigger — we move a context to hexagonal only when at least
   one of these is true:
   - it accumulates 3+ interacting business rules,
   - its logic can no longer be tested without live infrastructure,
   - a second adapter becomes real (e.g., Kafka alongside MQTT).

## Consequences
Positive:
- File count and reading time stay proportional to actual complexity.
- The architecture choice is *deliberate and documented*, which reads
  stronger in review than uniform pattern-worship either direction.
- Pure core functions (`allocate`, payload transforms) are testable today.

Trade-offs:
- Route handlers couple directly to FastAPI/SQLAlchemy; swapping storage
  means editing handlers.
- No compiler-enforced dependency direction; discipline, this ADR, and
  tests enforce it instead.

## Related
- ADR-001 (database isolation), ADR-002 (service autonomy)
- Future: ADR-004 (transactional outbox)