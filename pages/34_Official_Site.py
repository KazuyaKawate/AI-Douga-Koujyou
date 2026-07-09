from __future__ import annotations

import streamlit as st

from src.official_site.site_manager import (
    DEFAULT_SITE_URL,
    article_list,
    deploy_site,
    formal_release,
    load_business_engine,
    preflight_check,
    production_check,
    publication_summary,
    seo_queue,
    write_html_site,
    write_site_artifacts,
)
from src.official_site.website_engine import WebsiteEngine
from src.utils.settings_manager import load_settings, save_settings


st.set_page_config(page_title="AIOS Official Site", page_icon="🌐", layout="wide")

st.title("🌐 AIOS公式サイト管理")
st.caption("Phase4: AIOSの収益導線となる公式サイトをLocal First / DryRunで生成します。")

data = load_business_engine()
website_engine = WebsiteEngine()
website_state = website_engine.load_state()
website_context = website_state.get("last_build", {})
settings = load_settings()
release_settings = settings.setdefault("release", {})
seo_items = seo_queue(data)
articles = article_list(data)
status_counts = publication_summary(data)

st.subheader("初回セットアップ")
setup_cols = st.columns(2)
with setup_cols[0]:
    site_url = st.text_input("独自ドメイン", value=release_settings.get("domain_url", DEFAULT_SITE_URL))
    public_dir = st.text_input("公開ディレクトリ", value=release_settings.get("public_dir", ""))
    vps_host = st.text_input("VPS Host", value=release_settings.get("vps_host", ""))
    vps_user = st.text_input("VPS User", value=release_settings.get("vps_user", "deploy"))
    vps_web_root = st.text_input("VPS Web Root", value=release_settings.get("vps_web_root", "/var/www/aios"))
    ga_id = st.text_input("Google Analytics", value=release_settings.get("google_analytics_id", ""))
with setup_cols[1]:
    gsc_token = st.text_input("Search Console", value=release_settings.get("search_console_verification", ""))
    gsc_file = st.text_input("Search Console File", value=release_settings.get("search_console_file", ""))
    gsc_file_content = st.text_area("Search Console File Content", value=release_settings.get("search_console_file_content", ""), height=80)
    review_approved = st.checkbox("公開前レビュー承認", value=bool(release_settings.get("pre_publication_review_approved", False)))
    threads_token = st.text_input("Threads Token", value=release_settings.get("threads_access_token", ""), type="password")
    threads_user_id = st.text_input("Threads User ID", value=release_settings.get("threads_user_id", ""))

if st.button("初回セットアップを保存", type="primary"):
    settings["release"] = {
        **release_settings,
        "domain_url": site_url.strip(),
        "public_dir": public_dir.strip(),
        "vps_host": vps_host.strip(),
        "vps_user": vps_user.strip(),
        "vps_web_root": vps_web_root.strip(),
        "google_analytics_id": ga_id.strip(),
        "search_console_verification": gsc_token.strip(),
        "search_console_file": gsc_file.strip(),
        "search_console_file_content": gsc_file_content.strip(),
        "pre_publication_review_approved": bool(review_approved),
        "threads_access_token": threads_token.strip(),
        "threads_user_id": threads_user_id.strip(),
    }
    save_settings(settings)
    st.success("Release設定を保存しました。")
    st.rerun()

phase_cols = st.columns(4)
phase_cols[0].metric("Local First", "ON")
phase_cols[1].metric("DryRun", "ON")
phase_cols[2].metric("最新Build", website_context.get("created_at", "None"))
phase_cols[3].metric("出力先", "output/official_website")

cols = st.columns(4)
cols[0].metric("SEO Queue", len(seo_items))
cols[1].metric("Articles", len(articles))
cols[2].metric("Published", status_counts.get("published", 0) + status_counts.get("posted", 0))
cols[3].metric("Draft / Queued", status_counts.get("draft", 0) + status_counts.get("queued", 0))

st.divider()

tab_hub, tab_seo, tab_articles, tab_artifacts, tab_phase5, tab_release = st.tabs(["Business Hub", "SEOキュー", "記事一覧", "サイトファイル", "Phase5公開準備", "正式公開"])

with tab_hub:
    st.subheader("AIOS公式サイト Phase4")
    st.caption("トップ / AIOS紹介 / 特徴 / 利用開始 / 料金 / ブログ / note / Threads / お問い合わせ / 更新履歴を統合生成します。")
    hub_cols = st.columns(5)
    hub_cols[0].metric("PV", website_state.get("analytics", {}).get("pv", 0))
    hub_cols[1].metric("CTR", website_state.get("analytics", {}).get("ctr", 0))
    hub_cols[2].metric("Revenue", f"¥{int(website_state.get('analytics', {}).get('revenue', 0)):,}")
    hub_cols[3].metric("Contacts", website_state.get("analytics", {}).get("contact_count", 0))
    hub_cols[4].metric("Users", website_state.get("analytics", {}).get("registered_users", 0))

    action_cols = st.columns([1, 1, 2])
    if action_cols[0].button("Business Hub生成", type="primary", use_container_width=True):
        result = website_engine.build_site(site_url)
        st.success(f"Business Hubを生成しました: {len(result['written'])} files")
        st.rerun()
    if action_cols[1].button("管理状態を更新", use_container_width=True):
        website_engine.build_site(site_url)
        st.rerun()
    action_cols[2].code("生成先: output/official_website", language="text")

    with st.expander("トップページ連携データ", expanded=True):
        st.json({
            "latest_articles": "Business Engine + Content Factory contents",
            "popular_articles": "PV/CTR sorted",
            "revenue_kpi": "Business Engine weighted forecast and article revenue",
            "first_revenue_progress": "Business Engine Phase1 dashboard",
            "content_factory_auto_reflect": "config/content_factory.json contents are imported on build",
        })

    st.markdown("**問い合わせ / ユーザー登録**")
    form_cols = st.columns(2)
    with form_cols[0]:
        contact_name = st.text_input("Name", key="web_contact_name")
        contact_email = st.text_input("Email", key="web_contact_email")
        contact_message = st.text_area("Message", key="web_contact_message")
        if st.button("問い合わせを保存"):
            website_engine.register_contact(contact_name, contact_email, contact_message)
            st.success("問い合わせを保存しました。")
            st.rerun()
    with form_cols[1]:
        user_email = st.text_input("User Email", key="web_user_email")
        user_plan = st.selectbox("Plan", ["Free", "Pro", "Business"], key="web_user_plan")
        if st.button("ユーザー登録"):
            website_engine.register_user(user_email, user_plan)
            st.success("ユーザーを登録しました。")
            st.rerun()

    with st.expander("管理者Dashboard"):
        st.json({
            "last_build": website_state.get("last_build", {}),
            "release_notes": website_state.get("release_notes", [])[:5],
            "mission_feedback": website_state.get("mission_feedback", [])[:5],
            "contacts": website_state.get("contacts", [])[:5],
            "users": website_state.get("users", [])[:5],
        })

with tab_seo:
    if not seo_items:
        st.info("SEOキューは空です。")
    for item in seo_items:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            c1.markdown(f"**{item.get('keyword', '')}**")
            c2.caption(f"intent: {item.get('intent', '')}")
            c3.metric("status", item.get("status", ""))
            c4.metric("priority", item.get("priority", ""))

with tab_articles:
    if not articles:
        st.info("記事はまだありません。")
    for article in articles:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 2])
            c1.markdown(f"**{article.get('title', 'Untitled')}**")
            c1.caption(article.get("keyword") or article.get("topic") or "")
            c2.metric("status", article.get("status", ""))
            c3.caption(article.get("markdown_path") or article.get("created_at") or "")

with tab_artifacts:
    st.caption("生成先: output/official_site/")
    if st.button("HTMLサイト一式を生成", type="primary"):
        artifacts = write_html_site(
            data,
            site_url,
            google_analytics_id=ga_id.strip(),
            search_console_verification=gsc_token.strip(),
        )
        st.success("公開用HTMLサイトを生成しました。")
        for name, path in artifacts.items():
            st.code(f"{name}: {path}", language="text")

with tab_phase5:
    st.subheader("Phase5 公開準備")
    st.caption("VPS公開・独自ドメイン・HTTPS・GSC・GAをDryRunで準備します。公開前レビュー承認が必須です。")
    p5_cols = st.columns(4)
    p5_cols[0].metric("VPS", "OK" if vps_host.strip() else "未設定")
    p5_cols[1].metric("HTTPS", "OK" if site_url.strip().startswith("https://") else "NG")
    p5_cols[2].metric("GSC", "OK" if (gsc_token.strip() or gsc_file.strip()) else "未設定")
    p5_cols[3].metric("GA", "OK" if ga_id.strip() else "未設定")

    if st.button("Phase5 DryRun公開準備 + 公開前レビュー", type="primary"):
        current_settings = {
            **settings,
            "release": {
                **release_settings,
                "domain_url": site_url.strip(),
                "public_dir": public_dir.strip(),
                "vps_host": vps_host.strip(),
                "vps_user": vps_user.strip(),
                "vps_web_root": vps_web_root.strip(),
                "google_analytics_id": ga_id.strip(),
                "search_console_verification": gsc_token.strip(),
                "search_console_file": gsc_file.strip(),
                "search_console_file_content": gsc_file_content.strip(),
                "pre_publication_review_approved": bool(review_approved),
            },
        }
        result = website_engine.build_phase5_release(current_settings)
        review = result["review"]
        if review["publish_ready"]:
            st.success("Review Gate: publish_ready=true")
        else:
            st.error("Review Gate: publish_ready=false")
        st.json(review)
        st.code(result["deploy_plan"]["commands"], language="text")

    phase5_state = website_state.get("phase5_release", {})
    if phase5_state:
        review = phase5_state.get("review", {})
        st.markdown("**公開前レビュー画面**")
        rg_cols = st.columns(4)
        rg_cols[0].metric("publish_ready", str(review.get("publish_ready", False)).lower())
        rg_cols[1].metric("公開対象記事数", review.get("target_article_count", 0))
        rg_cols[2].metric("未公開記事数", review.get("unpublished_article_count", 0))
        rg_cols[3].metric("エラー数", len(review.get("errors", [])))
        st.caption(f"サイトURL: {review.get('site_url', '')}")
        st.caption(f"独自ドメイン: {review.get('domain', '')}")
        st.caption(f"HTTPS設定: {'ON' if review.get('https_enabled') else 'OFF'}")
        checks = review.get("checks", [])
        if checks:
            st.dataframe(checks, use_container_width=True, hide_index=True)
        if review.get("errors"):
            st.markdown("**エラー一覧**")
            st.dataframe(review["errors"], use_container_width=True, hide_index=True)
        else:
            st.success("Review Gate エラーはありません。")
        st.markdown("**DryRunデプロイ計画**")
        st.json(phase5_state.get("deploy_plan", {}))

    if st.button("公開前チェック"):
        result = preflight_check()
        if result["ok"]:
            st.success(f"公開前チェックOK: HTML {result['checked_html']}件")
        else:
            st.error("公開前チェックで問題が見つかりました。")
        for error in result["errors"]:
            st.code(error, language="text")
        for warning in result["warnings"]:
            st.warning(warning)

    if st.button("公開ディレクトリへコピー"):
        if not public_dir.strip():
            st.error("公開ディレクトリを入力してください。")
        else:
            deployed = deploy_site(public_dir.strip())
            st.success("公開ディレクトリへコピーしました。")
            st.code(f"source: {deployed['source']}\ntarget: {deployed['target']}", language="text")

    if st.button("sitemap / robots.txt / RSS を生成", type="primary"):
        artifacts = write_site_artifacts(data, site_url)
        st.success("公式サイト用ファイルを生成しました。")
        for name, path in artifacts.items():
            st.code(f"{name}: {path}", language="text")

with tab_release:
    st.subheader("設定確認")
    masked = {
        **release_settings,
        "threads_access_token": "設定済み" if release_settings.get("threads_access_token") else "",
    }
    st.json(masked)

    if st.button("本番環境チェック"):
        result = production_check(settings)
        for name, ok in result["checks"].items():
            st.write(f"{'OK' if ok else 'NG'}: {name}")
        if result["ok"]:
            st.success("本番環境チェックOK")
        else:
            st.error("不足: " + ", ".join(result["missing"]))

    if st.button("正式公開", type="primary"):
        try:
            result = formal_release(data, settings)
            save_settings(result["settings"])
            st.success("正式Releaseへ移行しました。")
            st.code(f"target: {result['deployed']['target']}", language="text")
        except Exception as exc:
            st.error(str(exc))
