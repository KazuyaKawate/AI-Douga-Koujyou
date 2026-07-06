from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.version import get_version_label
from src.export.export_manager import ExportManager

st.set_page_config(page_title="Export Manager | AIOS", page_icon="📦", layout="wide")

manager = ExportManager()
summary = manager.summary()
ready_items = manager.publish_ready_items()

st.title("📦 Export Manager")
st.caption(f"Local publishing/export pipeline | {get_version_label()} | External publishing disabled")
st.info("Local-first mode: exports are written only to local folders under output/. No upload, cloud sync, or external publishing is performed.")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Pending Exports", summary["pending_exports"])
m2.metric("Completed Exports", summary["completed_exports"])
m3.metric("Failed Exports", summary["failed_exports"])
m4.metric("Latest Export", summary["latest_export"])
m5.metric("Total Exported", summary["total_exported"])
m6.metric("Export Size", f"{summary['export_size'] / 1024:.1f} KB")

tabs = st.tabs([
    "📥 Export Queue",
    "✅ Export History",
    "📦 Package Builder",
    "🧾 Export Logs",
    "📊 Summary",
])

with tabs[0]:
    st.subheader("📥 Export Queue")
    st.caption("Only Approval Center items with status publish_ready can be queued.")

    if ready_items:
        st.markdown("**Publish-ready approval items**")
        for item in ready_items:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.markdown(f"**{item.get('title', '')}**  \n`{item.get('content_type', '')}` / `{item.get('id', '')}`")
                c2.metric("Risk Flags", len(item.get("risk_flags", [])))
                with c3:
                    if st.button("Queue export", key=f"queue_{item['id']}", use_container_width=True):
                        try:
                            manager.queue_export(item["id"])
                            st.success("Queued for local export.")
                            st.rerun()
                        except ValueError as exc:
                            st.error(str(exc))
    else:
        st.info("No publish-ready content is available.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Queue all publish-ready", type="primary", use_container_width=True):
            queued = manager.queue_all_publish_ready()
            st.success(f"Queued {len(queued)} export(s).")
            st.rerun()
    with col_b:
        if st.button("Run batch export", use_container_width=True):
            results = manager.export_batch()
            st.success(f"Processed {len(results)} export(s).")
            st.rerun()

    st.divider()
    queue = summary["queue"]
    if not queue:
        st.info("Export queue is empty.")
    for record in queue:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{record.get('title', '')}**  \n`{record.get('export_id', '')}` / `{record.get('content_type', '')}`")
            c2.metric("Status", record.get("export_status", ""))
            c3.metric("Attempts", record.get("attempts", 0))
            with c4:
                if st.button("Export", key=f"export_{record['export_id']}", use_container_width=True):
                    manager.export_one(record["export_id"])
                    st.rerun()
                if record.get("export_status") == "failed" and st.button("Retry", key=f"retry_{record['export_id']}", use_container_width=True):
                    manager.retry_export(record["export_id"])
                    st.rerun()
                if st.button("Delete", key=f"delete_{record['export_id']}", use_container_width=True):
                    manager.delete_export_record(record["export_id"])
                    st.rerun()
            if record.get("last_error"):
                st.warning(record["last_error"])

with tabs[1]:
    st.subheader("✅ Export History")
    if st.button("Clear completed export records"):
        cleared = manager.clear_completed_exports()
        st.success(f"Cleared {cleared} completed record(s).")
        st.rerun()
    history = summary["history"]
    if not history:
        st.info("No export history yet.")
    for record in history[:100]:
        with st.expander(f"{record.get('export_status')} — {record.get('title', '')} — {record.get('exported_at', '')}", expanded=False):
            st.json(record)

with tabs[2]:
    st.subheader("📦 Package Builder")
    st.caption("Builds a ZIP package from publish-ready content only.")
    selectable = {f"{item.get('title', '')} ({item.get('id', '')})": item["id"] for item in ready_items}
    selected_labels = st.multiselect("Package items", list(selectable.keys()), default=list(selectable.keys()))
    selected_ids = [selectable[label] for label in selected_labels]
    if st.button("Build local ZIP package", type="primary"):
        try:
            package = manager.build_package(selected_ids)
            st.success(f"Package created: {package['zip_path']}")
            st.json(package)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.markdown("**Local packages**")
    if not summary["packages"]:
        st.info("No packages created yet.")
    for package in summary["packages"][:50]:
        st.write(f"{package.get('created_at')} — `{package.get('package_id')}` — {package.get('zip_path')} ({package.get('file_size', 0)} bytes)")

with tabs[3]:
    st.subheader("🧾 Export Logs")
    logs = summary["logs"]
    if not logs:
        st.info("No export logs yet.")
    for row in logs[:200]:
        st.write(f"{row.get('created_at')} — `{row.get('status')}` — {row.get('export_id')} — {row.get('message')}")

with tabs[4]:
    st.subheader("📊 Export Summary")
    st.json({
        "local_only": True,
        "external_publish_enabled": False,
        "pending_exports": summary["pending_exports"],
        "completed_exports": summary["completed_exports"],
        "failed_exports": summary["failed_exports"],
        "total_exported": summary["total_exported"],
        "total_local_packages": summary["total_local_packages"],
        "export_size": summary["export_size"],
        "output_root": str(manager.output_root),
    })
