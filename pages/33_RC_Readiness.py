from __future__ import annotations

import streamlit as st

from src.rc.rc_manager import RCReadinessManager

st.set_page_config(page_title="RC Readiness", page_icon="🚦", layout="wide")

manager = RCReadinessManager()
report = manager.collect()

st.title("🚦 AIOS RC Readiness")
st.caption(f"{report['rc_name']} | {report['version']} | Local-first release gate")
st.info("Local-first RC gate: no OpenAI, Anthropic, Gemini Cloud, Google Workspace, external publishing, or upload path is enabled.")

r1, r2, r3, r4 = st.columns(4)
r1.metric("RC Ready", "YES" if report["ready"] else "NO")
r2.metric("Blockers", len(report["blockers"]))
r3.metric("Warnings", len(report["warnings"]))
r4.metric("Generated", report["generated_at"])

tabs = st.tabs(["Safety", "Modules", "Warnings", "Manifest"])

with tabs[0]:
    st.subheader("Local-First Safety")
    for key, ok in report["safety"].items():
        st.write(f"{'OK' if ok else 'NG'} — {key}")

with tabs[1]:
    st.subheader("Integrated Modules")
    for name, item in report["modules"].items():
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.metric("Ready", "YES" if item.get("ready") else "NO")
            st.json(item.get("metrics", {}))

with tabs[2]:
    st.subheader("Warnings and Blockers")
    if report["blockers"]:
        st.error("Blockers detected")
        for blocker in report["blockers"]:
            st.write(f"- {blocker}")
    else:
        st.success("No RC blockers detected.")
    if report["warnings"]:
        st.warning("Warnings")
        for warning in report["warnings"]:
            st.write(f"- {warning}")
    else:
        st.info("No warnings detected.")

with tabs[3]:
    st.subheader("RC Manifest")
    if st.button("Write local RC manifest", type="primary"):
        path = manager.write_manifest()
        st.success(f"Manifest written locally: {path}")
    st.json(report)
