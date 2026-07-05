"""Dashboard 共通ユーティリティ。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# プロジェクトルートを sys.path に追加（dashboard/ から起動する場合）
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_ROOT / ".env", override=False)


def init_kernel():
    """Kernel を初期化して返す。StreamlitのキャッシュはTTL付きで保持。"""
    from src.core.kernel import get_kernel
    from src.ai_agents.registry import get_agent_registry
    k = get_kernel()
    reg = get_agent_registry()
    reg.auto_load()
    return k


def run_workflow_tracked(workflow_name: str, context: dict) -> tuple[object, float]:
    """
    Workflow を実行して (WorkflowStatus, duration_sec) を返す。
    ExecutionTracker に自動記録する。
    """
    from src.intelligence.tracker import get_tracker
    kernel = init_kernel()
    t0     = time.monotonic()
    status = kernel.run_workflow(workflow_name, context)
    dur_ms = int((time.monotonic() - t0) * 1000)

    success  = getattr(status, "success", True)
    out_text = ""
    try:
        for step_s in getattr(status, "step_statuses", {}).values():
            out_text += str(step_s.output or "")
    except Exception:
        pass

    get_tracker().record(
        workflow_name = workflow_name,
        factory_id    = workflow_name.split(".")[0],
        success       = success,
        duration_ms   = dur_ms,
        output_chars  = len(out_text),
    )
    return status, dur_ms / 1000


def get_workflow_output(status) -> str:
    """WorkflowStatus から最終出力テキストを抽出する。"""
    try:
        ctx = getattr(status, "context", {})
        if not ctx:
            return ""
        # コンテキストの最後の値を返す（通常が最終出力）
        vals = [v for v in ctx.values() if isinstance(v, str) and len(v) > 20]
        return vals[-1] if vals else ""
    except Exception:
        return ""


FACTORY_ICONS = {
    "social":       "📱",
    "video":        "🎬",
    "research":     "🔬",
    "writing":      "✍️",
    "fortune":      "🔮",
    "store":        "🛒",
    "intelligence": "🧠",
    "composer":     "🎵",
    "job_scheduler":"⏰",
    "demo_plugin":  "🧪",
    "marketing":    "📊",
    "creator":      "🎨",
}

STATUS_COLORS = {
    "active":   "#28a745",
    "paused":   "#ffc107",
    "finished": "#6c757d",
    "failed":   "#dc3545",
}
