# Factory Specification — Creator Factory OS v4.5.1

> Every Factory in Creator Factory OS must comply with this specification.
> Factories are modules within a Project. Projects are the top-level unit.

---

## 1. Folder Structure

```
src/factories/<factory_slug>/
├── __init__.py             # Package marker
├── <noun>_manager.py       # Primary data CRUD (load / save / create / update / delete)
├── <noun>_<verb>.py        # Additional domain logic (scorer, tracker, calculator, etc.)
└── ...
```

**Registered factory slugs:**

| Slug | Factory Name | Version |
|------|--------------|---------|
| `note/` | note投稿工場 | 4.3 |
| `sns/` | SNS投稿工場 | 4.4 |
| `sales/` | 営業工場 | 4.5 |
| `accounting/` | 会計監査工場 | 4.6 |

Dev-tools (non-data factories) live in `src/devtools/`.
AI core pipeline lives in `src/core/` (pre-v4.3 legacy).

---

## 2. Required Files

| File | Purpose |
|------|---------|
| `src/factories/<slug>/__init__.py` | Python package marker |
| `src/factories/<slug>/<primary>_manager.py` | CRUD for primary data entity |
| `pages/<N>_<FactoryName>.py` | Streamlit page (6-tab minimum) |
| `config/<slug>_<entity>.json` | JSON data store for each entity |

---

## 3. Required Methods (FactoryBase interface)

Each factory must expose an adapter class that inherits `src.core.factory_base.FactoryBase`.

```python
class MyFactoryAdapter(FactoryBase):
    NAME    = "my工場"
    VERSION = "4.x"
    ICON    = "🏭"
    DEPENDENCIES: list[str] = []

    def initialize(self) -> bool: ...
    def health_check(self) -> HealthReport: ...
    def sync_kpi(self) -> dict: ...
    def sync_dashboard(self) -> dict: ...
    def sync_mission_control(self) -> FactoryStatus: ...
    def generate_report(self, year_month: str = "") -> str: ...
    def export_status(self) -> dict: ...
```

**Method contract:**

| Method | Return | Description |
|--------|--------|-------------|
| `initialize()` | `bool` | Set up config files / defaults. Return True on success |
| `health_check()` | `HealthReport` | Check config files, data integrity. Return severity |
| `sync_kpi()` | `dict` | Read factory data and return KPI values for kpi_targets.json |
| `sync_dashboard()` | `dict` | Return 4–8 metric values for Dashboard strip |
| `sync_mission_control()` | `FactoryStatus` | Return status card data for Mission Control |
| `generate_report(year_month)` | `str` | Generate Markdown report for given month |
| `export_status()` | `dict` | Snapshot of current factory state as JSON-serializable dict |

---

## 4. Required Config Format

Every factory JSON config must include a `meta` block:

```json
{
  "<entity_key>": [],
  "meta": {
    "version": "4.x",
    "created_at": "YYYY-MM-DD"
  }
}
```

**Config file naming:** `config/<factory_slug>_<entity>.json`

Examples:
- `config/note_articles.json` → key `"articles"`
- `config/sales_leads.json` → key `"leads"`
- `config/accounting_revenue.json` → key `"revenue"`

---

## 5. Required Integrations

### 5.1 Mission Control

Every factory must be registered in `src/hq/factory_status.py`:

```python
def sync_from_<factory>(factory_data: dict) -> dict:
    try:
        from src.factories.<slug>.<primary>_manager import load_<entity>, get_factory_summary
        ...
        if "<工場名>" in factory_data:
            fd = factory_data["<工場名>"]
            fd["active_items"]    = ...
            fd["warning_count"]   = ...
            fd["completed_today"] = ...
            fd["status"]          = ...
            fd["next_action"]     = ...
    except Exception:
        pass
    return factory_data
```

### 5.2 Dashboard

Add a summary strip to `pages/8_Dashboard.py` with 4–8 `st.metric()` cards.

### 5.3 Factory Registry

Add an entry to `FACTORY_CATALOG` in `src/core/factory_registry.py`:

```python
"<工場名>": {
    "name":         "<工場名>",
    "icon":         "<icon>",
    "version":      "4.x",
    "module_path":  "src.factories.<slug>",
    "page":         "pages/<N>_<FactoryPage>.py",
    "config_files": ["config/<slug>_<entity>.json"],
    "dependencies": [],
    "description":  "<description>",
},
```

### 5.4 Project Registry

A factory added to `FACTORY_CATALOG` is automatically available to be assigned to any Project.

---

## 6. Design Constraints

| Constraint | Rule |
|------------|------|
| **No external API calls** | All logic is rule-based. OpenAI is used only in `src/core/ai_pipeline.py` (AI Video Factory) |
| **Local JSON storage** | All data in `config/`. No database |
| **Additive only** | New factories must not modify existing factory modules |
| **Lazy imports** | Cross-factory imports must be inside function bodies (not at module top) |
| **Path depth** | `src/factories/<slug>/` modules use 4× `.parent` to reach project root |
| **Status lifecycle** | Every entity must have a `status` field with defined transitions |

---

## 7. Page Structure (Streamlit)

Minimum 6 tabs per factory page:

| Tab | Purpose |
|-----|---------|
| ダッシュボード | Summary metrics + top alerts + quick action |
| <Primary entity> | CRUD list with filter + search |
| <Secondary entity> | CRUD list or workflow view |
| <Tertiary entity> | Supporting feature |
| 分析 / レポート | Aggregated analytics or report export |
| 設定 | Factory settings (configurable thresholds, etc.) |

---

## 8. Health Check Registration

Add to `scripts/check_project.py`:

```python
REQUIRED_FOLDERS += ["src/factories/<slug>"]
REQUIRED_FILES   += [
    "pages/<N>_<FactoryPage>.py",
    "src/factories/<slug>/__init__.py",
    "src/factories/<slug>/<primary>_manager.py",
    ...
]
OPTIONAL_FILES   += ["config/<slug>_<entity>.json"]
```
