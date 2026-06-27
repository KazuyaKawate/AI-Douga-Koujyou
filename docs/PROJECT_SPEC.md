# Project Specification — Creator Factory OS v4.5.1

> Creator Factory OS is **Project-centric**. A Project is the top-level unit of work.
> Factories are modules inside a Project.

---

## 1. Project Model

```python
@dataclass
class Project:
    project_id:  str          # "proj_" + 8-char uuid hex
    name:        str          # Display name
    owner:       str          # Creator / owner name
    factories:   list[str]    # Factory names assigned to this project
    status:      str          # active | paused | completed | archived
    revenue:     int          # Cumulative revenue in JPY
    priority:    int          # 1 (highest) – 5 (lowest)
    progress:    float        # 0–100 (manual or computed)
    description: str
    created_at:  str          # YYYY-MM-DD
    updated_at:  str          # YYYY-MM-DD
```

---

## 2. Project Lifecycle

```
┌──────────┐    create    ┌──────────┐    progress   ┌───────────┐
│  (none)  │ ──────────▶ │  active  │ ─────────────▶ │ completed │
└──────────┘             └──────────┘                └───────────┘
                              │  pause                     │
                              ▼                            │ archive
                         ┌──────────┐                      ▼
                         │  paused  │               ┌───────────┐
                         └──────────┘               │ archived  │
                              │  resume             └───────────┘
                              ▼
                         ┌──────────┐
                         │  active  │
                         └──────────┘
```

**Status rules:**

| Status | Meaning |
|--------|---------|
| `active` | Project is in progress — factories are running |
| `paused` | Temporarily halted — factories remain assigned but inactive |
| `completed` | All work done — revenue finalized |
| `archived` | Historical record only — excluded from active KPI aggregation |

---

## 3. Project Structure

```
config/projects.json
└── projects[]
    ├── project_id    ← unique key
    ├── name
    ├── owner
    ├── factories[]   ← list of Factory Names from FACTORY_CATALOG
    ├── status
    ├── revenue       ← cumulative JPY (manual or synced from 会計監査工場)
    ├── priority      ← 1–5
    ├── progress      ← 0–100
    ├── description
    ├── created_at
    └── updated_at
```

---

## 4. Project Workflow

### 4.1 Create Project

```python
from src.core.project_manager import create_project

create_project(
    name="YouTube Series: AI解説",
    owner="自分",
    factories=["AI動画工場", "SNS投稿工場", "note投稿工場"],
    description="AI解説動画シリーズ — 月10本目標",
    priority=1,
)
```

### 4.2 Assign Factories

A factory is assigned to a project by adding its name to `factories[]`.
Multiple projects can share the same factory (e.g., both use note投稿工場).

### 4.3 Project Health

`ProjectRegistry.get_project_factory_health(project_id)` runs lightweight health checks on every factory assigned to the project (config file existence check — no module imports).

### 4.4 Revenue Tracking

`revenue` is updated by:
- Manual entry via Project settings
- Sync from 会計監査工場 `accounting_revenue.json` (contracted_total, filtered by project tag — v5.0 roadmap)

### 4.5 Progress Tracking

`progress` (0–100) is updated manually or derived from factory KPIs.
Future: auto-computed from factory completion rates (v5.0 roadmap).

---

## 5. Project Registry

`src/core/project_registry.py` provides system-level aggregation:

```python
from src.core.project_registry import ProjectRegistry

ProjectRegistry.get_system_summary()
# → {total_projects, active_projects, total_factories, healthy_factories, health_pct, system_health}

ProjectRegistry.get_all_project_summaries()
# → list of project summary dicts

ProjectRegistry.get_project_factory_health(project_id)
# → {project_id, project_name, factory_count, healthy_count, factory_health[]}

ProjectRegistry.find_projects_by_factory("営業工場")
# → list of projects that use 営業工場
```

---

## 6. Mission Control — Project-Centric View

As of v4.5.1, Mission Control presents a **Projects** section alongside the existing Factory Status cards.

The architecture roadmap (v5.0) defines Mission Control as fully project-centric:
- Each project card shows assigned factories as sub-modules
- Factory Status section replaced by Project Status section
- KPIs aggregated per project, not per factory

---

## 7. Default Project

On first run, `project_manager.py` auto-creates:

```json
{
  "project_id": "proj_creator_factory",
  "name": "Creator Factory",
  "owner": "自分",
  "factories": ["AI動画工場", "note投稿工場", "SNS投稿工場", "承認アシスタント", "営業工場", "会計監査工場"],
  "status": "active",
  "revenue": 0,
  "priority": 1,
  "progress": 0.0,
  "description": "メインクリエイターファクトリー — 全工場を統合"
}
```

This default project contains all installed factories.
Additional projects can be created for specific series, clients, or campaigns.

---

## 8. Project Data Store

**File:** `config/projects.json`

```json
{
  "projects": [ { ...Project } ],
  "meta": { "version": "4.5.1", "created_at": "YYYY-MM-DD" }
}
```

**Location:** `Path(__file__).parent.parent.parent / "config" / "projects.json"` from `src/core/project_manager.py`.
