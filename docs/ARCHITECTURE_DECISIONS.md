# Architecture Decision Records — Creator Factory OS

> This document records significant architectural decisions made during the development of Creator Factory OS.
> Format: ADR-NNN (Architecture Decision Record).

---

## ADR-001 — Project-Centric Architecture

**Date:** 2026-06-27
**Version:** v4.5.1
**Status:** Accepted

### Decision

Creator Factory OS is restructured as a **Project-centric** system.
Projects are the top-level unit. Factories are modules within a Project.

### Reason

Prior to v4.5.1, Creator Factory OS was factory-centric: factories were the top-level organizational unit. As more factories were added (Note, SNS, Sales, Accounting), the need for a higher-level grouping became clear. A creator may run multiple simultaneous projects (e.g., YouTube series + consulting business + SaaS product) each using different subsets of factories.

### Expected Benefit

- Group factories by business context rather than by technology
- Enable project-level revenue tracking and progress aggregation
- Prepare for multi-project dashboards and project-specific KPI targets
- Lay foundation for cross-factory automation (factory events trigger within a project scope)

### Trade-offs

- Additive layer — does not break existing factory-centric pages
- Projects are optional metadata; all factories continue to work without project assignment
- Full project-centric Mission Control deferred to v5.0

---

## ADR-002 — FactoryBase Abstract Interface

**Date:** 2026-06-27
**Version:** v4.5.1
**Status:** Accepted

### Decision

Define `src.core.factory_base.FactoryBase` as an ABC with 7 required methods:
`initialize`, `health_check`, `sync_kpi`, `sync_dashboard`, `sync_mission_control`, `generate_report`, `export_status`.

### Reason

Existing factories (v4.3–v4.6) were implemented as module-level functions, not classes. To standardize the interface without modifying existing factory modules, adapter classes wrap them and implement FactoryBase. New factories should inherit FactoryBase directly.

### Expected Benefit

- Uniform interface for factory health checks, KPI sync, and report generation
- Enables `FactoryRegistry` to query any factory via a single protocol
- Supports future factory testing via mock adapters

### Trade-offs

- Existing factories do NOT inherit FactoryBase (would require modification)
- Adapter pattern adds a thin layer; evaluated as worth the clarity
- Python's `@runtime_checkable` Protocol provides structural type checking as a lighter alternative

---

## ADR-003 — Static Factory Catalog

**Date:** 2026-06-27
**Version:** v4.5.1
**Status:** Accepted

### Decision

`FACTORY_CATALOG` in `src/core/factory_registry.py` is a **static dict** defined at module import time. No dynamic discovery (e.g., filesystem scanning or plugin loading).

### Reason

Dynamic discovery introduces complexity: file-watching, import errors, partial loading, security risks. At the current scale (6 factories), a static catalog is simpler and faster. Every new factory requires an explicit catalog entry anyway (it needs a page, config files, and dependencies declared).

### Expected Benefit

- Zero import cost at startup — factory modules are NOT imported by the registry
- Config file existence checks are the only I/O on health check
- Predictable: catalog reflects architect's intent, not filesystem state

### Trade-offs

- Adding a factory requires updating `FACTORY_CATALOG` manually
- Dynamic plugin discovery deferred to v5.0 if factory count grows > 10

---

## ADR-004 — Event Bus with JSON Persistence

**Date:** 2026-06-27
**Version:** v4.5.1
**Status:** Accepted

### Decision

`src.core.factory_events.EventBus` provides an in-process pub/sub system that persists events to `config/factory_events.json` (max 200 entries, FIFO eviction).

### Reason

Cross-factory side effects (e.g., closing a deal in 営業工場 → creating a revenue entry in 会計監査工場) require a decoupled signaling mechanism. Without an event system, each factory would need direct imports of other factories, creating coupling and potential circular imports.

### Expected Benefit

- Decoupled factory communication — emitter does not need to know subscribers
- Event history provides audit trail and debugging support
- Max 200 events keeps the JSON file small and load fast

### Trade-offs

- In-process only — no persistence across Streamlit sessions except via JSON
- Subscribers registered at import time; must be registered before first event
- Not a message queue — no retry, no guaranteed delivery
- Formal cross-factory automation deferred to v4.9

---

## ADR-005 — JSON-First Local Storage

**Date:** 2026-01-01 (v4.2)
**Version:** v4.2+
**Status:** Accepted (reaffirmed in v4.5.1)

### Decision

All data is stored in `config/*.json`. No SQLite, no PostgreSQL, no cloud database.

### Reason

Creator Factory OS is a single-creator local application. The creator's business data (leads, deals, revenue, articles) is personal and should not require a database server to operate. JSON files are human-readable, version-controllable, and trivially backed up.

### Expected Benefit

- Zero infrastructure: runs offline, no database setup
- All data visible and editable in any text editor
- Git can track data changes if the creator chooses to commit config/

### Trade-offs

- No concurrent writes — multi-tab access is not recommended
- JSON grows with data — not suitable for > ~10,000 records per file
- SQLite option planned as an optional backend for v5.0

---

## ADR-006 — Lazy Cross-Factory Imports

**Date:** 2026-06-27 (v4.4)
**Version:** v4.4+
**Status:** Accepted (reaffirmed in v4.5.1)

### Decision

All imports of one factory module from another factory module must be **inside function bodies** (lazy), never at module top level.

### Reason

Factory modules are Python packages. Circular imports at module level cause `ImportError` at startup. For example:
- `deal_manager.py` calls `factory_status.py` on contract close
- `factory_status.py` imports `deal_manager.py` for sync
Without lazy imports this is a circular dependency.

### Expected Benefit

- Zero circular import errors at startup
- Factory modules can be imported in any order
- Lazy imports only pay the import cost when the function is called

### Trade-offs

- Cross-factory calls are slightly harder to discover by static analysis
- Must be enforced by convention (no linter rule currently)

---

## ADR-007 — Additive-Only Development Rule

**Date:** 2026-06-27 (v4.3)
**Version:** v4.3+
**Status:** Accepted (reaffirmed in v4.5.1)

### Decision

Every version upgrade must be additive only:
- New factories do not modify existing factory modules
- New pages use new page numbers
- Existing config JSON files are not overwritten
- No factory behavior changes in upgrade commits

### Reason

Creator Factory OS accumulates business data over time. An upgrade that accidentally deletes or overwrites `config/sales_leads.json` would destroy the creator's CRM data. Strict additive-only discipline prevents data loss.

### Expected Benefit

- Safe to upgrade without backup
- Each version can be verified independently by running `scripts/check_project.py`
- Rollback is possible by reverting the new files only

### Trade-offs

- Cannot refactor existing factory internals in a version bump commit
- Refactors must be explicit "architecture-only" commits (like v4.5.1)
