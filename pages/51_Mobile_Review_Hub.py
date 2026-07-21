from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from src.business_engine.manager import BusinessEngineStore
from src.mobile_review_hub import CommonPublishQueue
from src.mobile_review_hub.security import csrf_valid, new_session, session_valid, verify_password
from src.note_workspace import NoteWorkspace
from src.publish_engine.gateway import PublishEngineGateway
from src.ui import apply_design_system, business_home_link, page_header, safety_status_strip
from src.ui.revenue2_first_customer import render_review_hub as render_revenue2_review
from src.ui.revenue4_onboarding import render_review_hub as render_revenue4_review
from src.ui.revenue5_owner_approval import render_review_hub as render_revenue5_review
from src.ui.revenue7_operation_simulation import render_review_hub as render_revenue7_review
from src.ui.revenue8_first_offer import render_review_hub as render_revenue8_review

st.set_page_config(page_title="Mobile Review Hub", page_icon="📱", layout="wide", initial_sidebar_state="collapsed")

apply_design_system()
business_home_link()
render_revenue2_review()
render_revenue4_review()
render_revenue5_review()
render_revenue7_review()
render_revenue8_review()

if not os.getenv("AIOS_MOBILE_REVIEW_PASSWORD"):
    st.error("Mobile Review Hubはロック中です。サーバー管理者が一時的な認証設定を行うまで利用できません。")
    st.stop()

session = st.session_state.get("mobile_hub_auth")
if not session_valid(session):
    page_header("Mobile Review Hub", "安全なモバイルレビュー認証が必要です。", eyebrow="AIOS / SECURE REVIEW")
    with st.form("mobile_login"):
        password = st.text_input("ログインパスワード", type="password")
        if st.form_submit_button("ログイン", type="primary", use_container_width=True):
            if verify_password(password): st.session_state["mobile_hub_auth"] = new_session(); st.rerun()
            else: st.error("認証に失敗しました。")
    st.caption("セッションは20分で失効します。認証情報は監査ログへ保存しません。")
    st.stop()

workspace = NoteWorkspace()
queue: CommonPublishQueue = workspace.mobile_review
publish_engine = PublishEngineGateway(queue=queue, note_workspace=workspace)
rows = queue.mobile_rows(); pending = [r for r in rows if r["status"] in {"review_required", "changes_requested", "approved", "ready_to_publish"}]
page_header("Mobile Review Hub", "全文確認・修正・承認・コピー・ダウンロード・公開事実登録。AIOSは公開／送信しません。", eyebrow="AIOS / MOBILE APPROVAL")
safety_status_strip()
st.markdown(f'<div class="hub-safe"><div>承認待ち<br><b>{len(pending)}</b></div><div>DryRun<br><b>ON</b></div><div>Review<br><b>Required</b></div><div>Production<br><b>OFF</b></div></div>', unsafe_allow_html=True)

if not rows: st.info("共通Publish Queueは空です。Commanderまたは各Workspaceから候補を追加してください。") ; st.stop()
labels = {f"{r['target_platform']}｜{r.get('title') or r.get('source_id')}｜{r['status']}": r["queue_id"] for r in rows}
selected_label = st.selectbox("公開候補", list(labels)); row = next(r for r in rows if r["queue_id"] == labels[selected_label])
st.markdown(f'<div class="hub-card"><b>{row["target_platform"].upper()}</b> · {row["status"]}<h3>{row.get("title") or "タイトルなし"}</h3><small>作成: {row.get("created_at","")} · Engine: {row.get("source_engine","")}</small></div>', unsafe_allow_html=True)
meta = st.columns(2); meta[0].write(f"タグ: {', '.join(row.get('tags', [])) or 'なし'}"); meta[1].write(f"価格: {row.get('price',0)}円 / {row.get('publication_type','draft')}")
st.write(f"CTA: {row.get('cta') or '未設定'}"); st.write(f"予定: {row.get('planned_publish_at') or '未設定'}"); st.code(row.get("content_hash", ""), language=None)
with st.expander("全文プレビュー", expanded=True): st.write(row.get("body") or "本文なし")
if row.get("target_platform") == "threads":
    st.text_area("Copy post text", value=row.get("body", ""), height=180, key=f"copy_{row['queue_id']}")
if row.get("image_path"): st.caption(f"アイキャッチ／画像: {row['image_path']}")
if row.get("review_result"): st.json(row["review_result"])
for warning in row.get("warnings", []): st.warning(warning)

with st.expander("Publication checklist", expanded=False):
    checklist = {
        "DryRun": row.get("dry_run") is True,
        "Review Required": row.get("review_required") is True,
        "Execute Blocked": row.get("execute_allowed") is False,
        "Title": bool(str(row.get("title", "")).strip()),
        "Body": bool(str(row.get("body", "")).strip()),
    }
    for label, passed in checklist.items(): st.write(f"{'✅' if passed else '⚠️'} {label}")
    st.download_button("Markdownをダウンロード", data=f"# {row.get('title', '')}\n\n{row.get('body', '')}", file_name=f"{row['queue_id']}.md", mime="text/markdown", use_container_width=True)

with st.expander("修正", expanded=False):
    with st.form(f"edit_{row['queue_id']}"):
        title = st.text_input("タイトル", value=row.get("title", "")); body = st.text_area("本文", value=row.get("body", ""), height=260); tags = st.text_input("タグ（カンマ区切り）", value=",".join(row.get("tags", []))); cta = st.text_input("CTA", value=row.get("cta", "")); price = st.number_input("価格", min_value=0, value=int(row.get("price", 0))); publication_type = st.selectbox("公開設定", ["draft", "public", "unlisted", "paid"], index=0); planned = st.text_input("投稿予定日時", value=row.get("planned_publish_at", "")); notes = st.text_area("備考", value=row.get("notes", "")); confirm_edit = st.checkbox("承認が失効し、再レビューになることを確認")
        if st.form_submit_button("修正を保存", use_container_width=True):
            if not confirm_edit or not csrf_valid(session, session["csrf_token"]): st.error("確認またはセッションが無効です。")
            else: queue.update(row["queue_id"], operator="mobile-human", title=title, body=body, tags=[x.strip() for x in tags.split(",") if x.strip()], cta=cta, price=int(price), publication_type=publication_type, planned_publish_at=planned, notes=notes); st.success("修正を保存し、承認を失効しました。") ; st.rerun()

with st.expander("公開完了を登録", expanded=False):
    with st.form(f"published_{row['queue_id']}"):
        public_url = st.text_input("公開URL"); public_at = st.text_input("公開日時", value=datetime.now().astimezone().isoformat(timespec="minutes")); confirmed_by = st.text_input("公開確認者", value="human"); external_id = st.text_input("記事ID／投稿ID"); public_notes = st.text_area("公開備考"); confirm_public = st.checkbox("人間が外部で公開／送信済みであることを確認")
        if st.form_submit_button("公開完了を登録", use_container_width=True):
            if not confirm_public: st.error("誤操作防止確認が必要です。")
            else:
                try:
                    recorder = None
                    if row.get("target_platform") == "note" and row.get("source_engine") == "note_workspace":
                        recorder = lambda item, record: workspace.record_manual_publish(
                            str(item["source_id"]), url=record["published_url"], published_at=record["published_at"],
                            publication_type=str(item.get("publication_type", "draft")), price=int(item.get("price", 0)),
                            confirmed_by=record["confirmed_by"], notes=record.get("publication_notes", ""), confirmed=True,
                        )
                    queue.record_published(row["queue_id"], url=public_url, published_at=public_at, confirmed_by=confirmed_by, external_id=external_id, notes=public_notes, confirmation_token=session["csrf_token"], canonical_recorder=recorder)
                    st.success("公開事実を登録しました。外部送信は行っていません。"); st.rerun()
                except ValueError as exc: st.error(str(exc))

with st.container(key="hub_action_bar"):
    st.caption("3タップ導線：候補を選ぶ → 内容を確認 → 承認／差し戻し（公開は外部で手動）")
    actions = st.columns(3)
    if actions[0].button("Request changes / 差し戻し", use_container_width=True):
        queue.request_changes(row["queue_id"], operator="mobile-human", reason="Mobile Review Hubから差し戻し"); st.rerun()
    if actions[1].button("Approve / 承認", type="primary", use_container_width=True, disabled=row["status"] not in {"review_required", "changes_requested"}):
        try:
            approved = queue.approve(row["queue_id"], approver="mobile-human", device_type="mobile", review_result="approved", confirmation_token=session["csrf_token"])
            if approved.get("target_platform") == "note" and approved.get("source_engine") == "note_workspace":
                publish_engine.dry_run_reviewed(approved["queue_id"])
            st.rerun()
        except ValueError as exc: st.error(str(exc))
    target_url = ""
    try: target_url = queue.open_target(row["queue_id"])
    except ValueError: pass
    actions[2].link_button("公開先を確認", target_url or "https://example.invalid/blocked", use_container_width=True, disabled=not bool(target_url))

with st.expander("その他の操作", expanded=False):
    secondary = st.columns(3)
    if secondary[0].button("Reject / 却下", use_container_width=True, disabled=row["status"] in {"rejected", "cancelled"}):
        queue.reject(row["queue_id"], operator="mobile-human", reason="Mobile Review Hubから却下"); st.rerun()
    if secondary[1].button("取消", use_container_width=True, disabled=row["status"] in {"rejected", "cancelled"}):
        queue.cancel(row["queue_id"], operator="mobile-human"); st.rerun()
    if row.get("target_platform") == "threads":
        if secondary[2].button("Threads DryRun", use_container_width=True, disabled=row["status"] != "ready_to_publish"):
            try: st.json(publish_engine.dry_run_reviewed(row["queue_id"]))
            except ValueError as exc: st.error(str(exc))
    elif secondary[2].button("公開完了を登録", use_container_width=True): st.info("上の『公開完了を登録』を開いてください。")

with st.expander("監査・デバッグ", expanded=False): st.json({"item": row, "history": queue.load()["history"][:20]})
