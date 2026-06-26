"""
SNS投稿工場 — Creator Factory OS v4.4
Platform-specific post creation from articles, video episodes, and ideas.
No external API calls. Rule-based formatting.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.factories.sns.sns_post_manager import (
    load_posts, create_post, update_post, delete_post, transition_status,
    get_posts_by_status, get_posts_by_platform, get_factory_summary,
    PLATFORMS, PLATFORM_LABELS, PLATFORM_ICONS, PLATFORM_LIMITS,
    SOURCE_TYPES, SOURCE_LABELS, STATUSES, STATUS_LABELS, STATUS_ICONS, TRANSITIONS,
)
from src.factories.sns.platform_formatter import format_post, format_all_platforms
from src.factories.sns.hashtag_generator import generate_hashtags, format_hashtags
from src.factories.sns.sns_calendar import (
    get_week_schedule, get_today_posts, get_overdue_posts, get_monthly_summary,
)
from src.factories.sns.sns_analytics_placeholder import (
    update_post_engagement, get_analytics_status,
)

APP_VERSION = "4.4"
TODAY = date.today()

st.set_page_config(
    page_title="SNS投稿工場 | Creator Factory OS",
    page_icon="📱",
    layout="wide",
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("📱 SNS投稿工場")
st.caption(f"プラットフォーム別投稿生成・管理・スケジュール | Creator Factory OS v{APP_VERSION} — SNS Factory")

# ── Load data ──────────────────────────────────────────────────────────────────
data = load_posts()
summary = get_factory_summary(data)
overdue = get_overdue_posts()

# Summary metrics
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("📄 下書き", summary["draft"])
m2.metric("🗓️ スケジュール済", summary["scheduled"])
m3.metric("✅ 公開済", summary["published"])
m4.metric("📅 今日の公開", summary["published_today"])
m5.metric("❤️ 総エンゲージメント", summary["total_engagement"])
m6.metric("⚠️ 期限超過", len(overdue), delta=None if not overdue else f"-{len(overdue)}", delta_color="inverse")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_dash, tab_create, tab_manage, tab_calendar, tab_repurpose, tab_analytics = st.tabs([
    "📊 ダッシュボード",
    "✏️ 投稿作成",
    "📋 投稿管理",
    "🗓️ カレンダー",
    "♻️ コンテンツ転用",
    "📈 分析",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_dash:
    st.subheader("📊 SNS Factory ダッシュボード")

    # Platform distribution
    st.markdown("**プラットフォーム別 投稿数**")
    by_platform = get_posts_by_platform(data)
    platform_cols = st.columns(7)
    for col, plat in zip(platform_cols, PLATFORMS):
        posts_for_plat = by_platform[plat]
        published = sum(1 for p in posts_for_plat if p.get("status") == "published")
        col.metric(
            f"{PLATFORM_ICONS[plat]} {PLATFORM_LABELS[plat].split(' ')[0]}",
            len(posts_for_plat),
            delta=f"{published}公開",
            delta_color="off",
        )

    st.divider()

    # Overdue warnings
    if overdue:
        st.warning(f"⚠️ {len(overdue)}件のスケジュール投稿が期限を過ぎています。「投稿管理」タブで確認してください。")

    # Today's posts
    today_posts = get_today_posts()
    st.subheader(f"📅 今日の投稿 ({TODAY.isoformat()})")
    if not today_posts:
        st.info("今日のスケジュール・公開済み投稿はありません。")
    else:
        for post in today_posts:
            plat = post.get("platform", "x")
            status = post.get("status", "draft")
            with st.container(border=True):
                pc1, pc2, pc3 = st.columns([1, 5, 2])
                pc1.markdown(f"**{PLATFORM_ICONS[plat]}**")
                pc2.markdown(f"**{post.get('title', '無題')}**")
                pc3.caption(f"{STATUS_ICONS[status]} {STATUS_LABELS[status]}")

    st.divider()

    # Recent published
    by_status = get_posts_by_status(data)
    recent_published = sorted(
        by_status["published"],
        key=lambda p: p.get("published_date", ""),
        reverse=True,
    )[:8]

    st.subheader("✅ 最近の公開投稿")
    if not recent_published:
        st.info("まだ公開済み投稿がありません。")
    else:
        for post in recent_published:
            plat = post.get("platform", "x")
            eng = post.get("engagement", {})
            total_eng = eng.get("likes", 0) + eng.get("comments", 0) + eng.get("shares", 0)
            rc1, rc2, rc3, rc4 = st.columns([1, 5, 2, 2])
            rc1.markdown(PLATFORM_ICONS[plat])
            rc2.markdown(f"**{post.get('title', '無題')}**")
            rc3.caption(post.get("published_date", ""))
            rc4.metric("エンゲージメント", total_eng)

    st.divider()

    # Monthly summary
    month_sum = get_monthly_summary()
    st.subheader(f"📆 今月 ({month_sum['year_month']}) サマリー")
    msc1, msc2 = st.columns(2)
    msc1.metric("今月の公開数", month_sum["total_published"])
    if month_sum["by_platform"]:
        top_plat = max(month_sum["by_platform"], key=lambda k: month_sum["by_platform"][k])
        msc2.metric("最多プラットフォーム", f"{PLATFORM_ICONS.get(top_plat, '')} {PLATFORM_LABELS.get(top_plat, top_plat)}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — POST CREATION
# ══════════════════════════════════════════════════════════════════════════════

with tab_create:
    st.subheader("✏️ 新規投稿を作成")

    cc1, cc2 = st.columns([2, 3])

    with cc1:
        st.markdown("**投稿設定**")

        new_title = st.text_input("投稿タイトル（管理用）*", placeholder="例: AIツール紹介 X投稿 06-27",
                                   key="create_title")
        new_source_type = st.selectbox(
            "コンテンツソース",
            SOURCE_TYPES,
            format_func=lambda s: SOURCE_LABELS[s],
            key="create_source",
        )
        new_platform = st.selectbox(
            "プラットフォーム *",
            PLATFORMS,
            format_func=lambda p: f"{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}",
            key="create_platform",
        )
        char_limit = PLATFORM_LIMITS[new_platform]
        st.caption(f"文字数上限: {char_limit:,} 文字")

        new_topic = st.text_input("テーマ・キーワード", placeholder="例: AI動画制作", key="create_topic")
        new_category = st.text_input("カテゴリ", placeholder="例: AI, 動画", key="create_cat")
        new_body = st.text_area("本文メモ・アウトライン（任意）", height=100, key="create_body",
                                 placeholder="箇条書きでポイントを入れると自動でテキスト生成します")
        new_scheduled = st.date_input("スケジュール日（任意）", value=None, key="create_sched")

        if st.button("🤖 テキスト自動生成", use_container_width=True, key="auto_gen"):
            if new_topic:
                result = format_post(
                    new_platform, new_topic, new_body, new_category,
                    source_title=new_title,
                )
                st.session_state["gen_text"] = result["text"]
                st.session_state["gen_hashtags"] = result["hashtags"]
            else:
                st.warning("テーマを入力してください")

    with cc2:
        st.markdown("**投稿テキスト**")

        default_text = st.session_state.get("gen_text", "")
        new_post_text = st.text_area(
            f"投稿テキスト（上限 {char_limit:,} 文字）",
            value=default_text,
            height=220,
            key="create_text",
        )
        char_now = len(new_post_text)
        over = char_now > char_limit
        st.caption(f"{char_now:,} / {char_limit:,} 文字 {'⚠️ 超過' if over else '✅'}")

        # Hashtags
        gen_tags = st.session_state.get("gen_hashtags", [])
        default_tag_str = ", ".join(gen_tags) if gen_tags else ""
        tag_str = st.text_input("ハッシュタグ（カンマ区切り）", value=default_tag_str, key="create_tags")
        tags_list = [t.strip().lstrip("#") for t in tag_str.split(",") if t.strip()]

        if tags_list:
            st.caption(format_hashtags(tags_list))

        st.divider()

        bc1, bc2, bc3 = st.columns(3)
        if bc1.button("💾 下書き保存", use_container_width=True, key="save_draft"):
            if not new_title.strip():
                st.error("タイトルを入力してください")
            elif not new_post_text.strip():
                st.error("投稿テキストを入力してください")
            else:
                create_post(
                    title=new_title.strip(),
                    platform=new_platform,
                    post_text=new_post_text,
                    hashtags=tags_list,
                    source_type=new_source_type,
                    scheduled_date=new_scheduled.isoformat() if new_scheduled else None,
                )
                st.success("✅ 下書きとして保存しました")
                for key in ("gen_text", "gen_hashtags"):
                    st.session_state.pop(key, None)
                st.rerun()

        if bc2.button("🗓️ スケジュール登録", use_container_width=True, key="save_sched"):
            if not new_title.strip():
                st.error("タイトルを入力してください")
            elif not new_post_text.strip():
                st.error("投稿テキストを入力してください")
            elif not new_scheduled:
                st.error("スケジュール日を選択してください")
            else:
                post = create_post(
                    title=new_title.strip(),
                    platform=new_platform,
                    post_text=new_post_text,
                    hashtags=tags_list,
                    source_type=new_source_type,
                    scheduled_date=new_scheduled.isoformat(),
                    status="scheduled",
                )
                st.success(f"🗓️ {new_scheduled} にスケジュール登録しました")
                for key in ("gen_text", "gen_hashtags"):
                    st.session_state.pop(key, None)
                st.rerun()

        if bc3.button("✅ 今すぐ公開", use_container_width=True, key="pub_now", type="primary"):
            if not new_title.strip():
                st.error("タイトルを入力してください")
            elif not new_post_text.strip():
                st.error("投稿テキストを入力してください")
            else:
                post = create_post(
                    title=new_title.strip(),
                    platform=new_platform,
                    post_text=new_post_text,
                    hashtags=tags_list,
                    source_type=new_source_type,
                )
                ok, msg, _ = transition_status(post["id"], "published")
                if ok:
                    st.success(f"✅ 公開しました！KPI更新済み")
                else:
                    st.error(msg)
                for key in ("gen_text", "gen_hashtags"):
                    st.session_state.pop(key, None)
                st.rerun()

        # All platforms preview
        if new_topic and st.button("🌐 全プラットフォームのプレビューを生成", use_container_width=True, key="preview_all"):
            st.session_state["all_previews"] = format_all_platforms(
                new_topic, new_body, new_category, source_title=new_title,
            )

        if st.session_state.get("all_previews"):
            st.markdown("**全プラットフォームプレビュー**")
            previews = st.session_state["all_previews"]
            for plat, preview in previews.items():
                with st.expander(f"{PLATFORM_ICONS[plat]} {PLATFORM_LABELS[plat]} ({preview['char_count']} 文字)"):
                    st.text_area("", value=preview["text"], height=120, key=f"prev_{plat}", disabled=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — POST MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

with tab_manage:
    st.subheader("📋 投稿管理")

    posts_all = data.get("posts", [])

    # Filters
    fc1, fc2 = st.columns(2)
    with fc1:
        filter_plat = st.selectbox(
            "プラットフォーム",
            ["すべて"] + PLATFORMS,
            format_func=lambda p: "すべて" if p == "すべて" else f"{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}",
            key="manage_plat",
        )
    with fc2:
        filter_status = st.selectbox(
            "ステータス",
            ["すべて"] + STATUSES,
            format_func=lambda s: "すべて" if s == "すべて" else f"{STATUS_ICONS[s]} {STATUS_LABELS[s]}",
            key="manage_status",
        )

    filtered = [
        p for p in posts_all
        if (filter_plat == "すべて" or p.get("platform") == filter_plat)
        and (filter_status == "すべて" or p.get("status") == filter_status)
    ]
    filtered.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    st.caption(f"{len(filtered)} / {len(posts_all)} 件")

    if not filtered:
        st.info("投稿がありません。「投稿作成」タブで投稿を作成してください。")

    for post in filtered:
        pid = post["id"]
        plat = post.get("platform", "x")
        status = post.get("status", "draft")
        eng = post.get("engagement", {})

        with st.expander(
            f"{PLATFORM_ICONS[plat]} {post.get('title', '無題')} [{STATUS_ICONS[status]} {STATUS_LABELS[status]}]",
            expanded=False,
        ):
            ec1, ec2 = st.columns([3, 2])

            with ec1:
                with st.form(f"edit_post_{pid}"):
                    e_title = st.text_input("タイトル", value=post.get("title", ""), key=f"et_{pid}")
                    e_plat = st.selectbox(
                        "プラットフォーム",
                        PLATFORMS,
                        index=PLATFORMS.index(plat) if plat in PLATFORMS else 0,
                        format_func=lambda p: f"{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}",
                        key=f"ep_{pid}",
                    )
                    e_text = st.text_area(
                        "投稿テキスト", value=post.get("post_text", ""),
                        height=150, key=f"etx_{pid}",
                    )
                    e_tag_str = st.text_input(
                        "ハッシュタグ", value=", ".join(post.get("hashtags", [])),
                        key=f"eht_{pid}",
                    )
                    e_sched = st.date_input(
                        "スケジュール日",
                        value=date.fromisoformat(post["scheduled_date"]) if post.get("scheduled_date") else None,
                        key=f"esd_{pid}",
                    )
                    char_count = len(e_text)
                    limit = PLATFORM_LIMITS.get(e_plat, 280)
                    st.caption(f"{char_count} / {limit} 文字 {'⚠️ 超過' if char_count > limit else '✅'}")
                    if st.form_submit_button("💾 保存"):
                        tags_upd = [t.strip().lstrip("#") for t in e_tag_str.split(",") if t.strip()]
                        update_post(
                            pid,
                            title=e_title,
                            platform=e_plat,
                            post_text=e_text,
                            hashtags=tags_upd,
                            scheduled_date=e_sched.isoformat() if e_sched else None,
                        )
                        st.success("保存しました")
                        st.rerun()

            with ec2:
                st.markdown("**ステータス変更**")
                st.caption(f"現在: {STATUS_ICONS[status]} {STATUS_LABELS[status]}")
                allowed = TRANSITIONS.get(status, [])
                for next_status in allowed:
                    btn_type = "primary" if next_status == "published" else "secondary"
                    if st.button(
                        f"{STATUS_ICONS[next_status]} → {STATUS_LABELS[next_status]}",
                        key=f"trans_{pid}_{next_status}",
                        use_container_width=True,
                        type=btn_type,
                    ):
                        ok, msg, _ = transition_status(pid, next_status)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                        st.rerun()

                st.divider()
                st.caption(f"作成: {post.get('created_at', '')}")
                if post.get("scheduled_date"):
                    st.caption(f"🗓️ 予定: {post['scheduled_date']}")
                if post.get("published_date"):
                    st.caption(f"✅ 公開: {post['published_date']}")

                if status == "published":
                    st.divider()
                    st.markdown("**エンゲージメント更新**")
                    with st.form(f"eng_{pid}"):
                        e_likes = st.number_input("❤️ いいね", min_value=0,
                                                   value=eng.get("likes", 0), key=f"el_{pid}")
                        e_com = st.number_input("💬 コメント", min_value=0,
                                                 value=eng.get("comments", 0), key=f"ec_{pid}")
                        e_sh = st.number_input("🔁 シェア", min_value=0,
                                               value=eng.get("shares", 0), key=f"es_{pid}")
                        e_reach = st.number_input("👁️ リーチ", min_value=0,
                                                   value=eng.get("reach", 0), key=f"er_{pid}")
                        if st.form_submit_button("💾 保存"):
                            update_post_engagement(pid, likes=e_likes, comments=e_com,
                                                    shares=e_sh, reach=e_reach)
                            st.success("保存しました")
                            st.rerun()

                st.divider()
                if st.button("🗑️ 削除", key=f"del_{pid}", use_container_width=True):
                    st.session_state[f"confirm_del_{pid}"] = True
                if st.session_state.get(f"confirm_del_{pid}"):
                    st.warning("削除しますか？")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("削除", key=f"del_yes_{pid}", type="primary"):
                        delete_post(pid)
                        st.session_state.pop(f"confirm_del_{pid}", None)
                        st.rerun()
                    if dc2.button("キャンセル", key=f"del_no_{pid}"):
                        st.session_state.pop(f"confirm_del_{pid}", None)
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

with tab_calendar:
    st.subheader("🗓️ 投稿カレンダー")

    cal_start = st.date_input("開始日", value=TODAY, key="cal_start")
    week_schedule = get_week_schedule(cal_start)

    st.markdown("**7日間のスケジュール**")
    for day_str, day_posts in week_schedule.items():
        day_obj = date.fromisoformat(day_str)
        label_suffix = ""
        if day_str == TODAY.isoformat():
            label_suffix = " ← 今日"
        elif day_obj < TODAY:
            label_suffix = " (過去)"

        day_label = f"**{day_obj.strftime('%m/%d (%a)')}**{label_suffix}"

        if not day_posts:
            with st.expander(day_label + " — 投稿なし", expanded=False):
                st.caption("この日の投稿はありません。")
        else:
            with st.expander(f"{day_label} — {len(day_posts)} 件", expanded=(day_str == TODAY.isoformat())):
                for post in day_posts:
                    plat = post.get("platform", "x")
                    status = post.get("status", "draft")
                    dc1, dc2, dc3 = st.columns([1, 5, 2])
                    dc1.markdown(PLATFORM_ICONS[plat])
                    dc2.markdown(f"{post.get('title', '無題')}")
                    dc3.caption(f"{STATUS_ICONS[status]} {STATUS_LABELS[status]}")

    st.divider()

    # Overdue section
    if overdue:
        st.subheader(f"⚠️ 期限超過 ({len(overdue)} 件)")
        for post in overdue:
            plat = post.get("platform", "x")
            with st.container(border=True):
                oc1, oc2, oc3, oc4 = st.columns([1, 4, 2, 2])
                oc1.markdown(PLATFORM_ICONS[plat])
                oc2.markdown(f"**{post.get('title', '無題')}**")
                oc3.caption(f"予定: {post.get('scheduled_date', '')}")
                if oc4.button("✅ 今すぐ公開", key=f"pub_overdue_{post['id']}", type="primary"):
                    ok, msg, _ = transition_status(post["id"], "published")
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CONTENT REPURPOSING
# ══════════════════════════════════════════════════════════════════════════════

with tab_repurpose:
    st.subheader("♻️ コンテンツ転用")
    st.caption("note記事・動画エピソードからSNS投稿を一括生成します。")

    rep_tab_note, rep_tab_video = st.tabs(["📝 note記事から転用", "🎬 動画エピソードから転用"])

    # ── Note articles ──────────────────────────────────────────────────────────
    with rep_tab_note:
        note_path = ROOT / "config" / "note_articles.json"
        if not note_path.exists():
            st.info("config/note_articles.json が見つかりません。note投稿工場で記事を作成してください。")
            st.page_link("pages/18_Note_Factory.py", label="📝 note投稿工場を開く →")
        else:
            try:
                note_data = json.loads(note_path.read_text(encoding="utf-8"))
                note_articles = note_data.get("articles", [])
                usable = [a for a in note_articles if a.get("status") in ("published", "draft", "reviewing")]
            except Exception:
                note_articles = []
                usable = []

            if not usable:
                st.info("転用可能な記事がありません（下書き・レビュー中・公開済みが対象）。")
            else:
                note_options = {f"{a.get('status','')}: {a['title']}": a["id"] for a in usable}
                selected_note_label = st.selectbox("転用元記事", list(note_options.keys()), key="rep_note_sel")
                selected_note_id = note_options[selected_note_label]
                selected_note = next((a for a in usable if a["id"] == selected_note_id), None)

                if selected_note:
                    st.markdown(f"**タイトル:** {selected_note.get('title','')}")
                    st.caption(f"キーワード: {selected_note.get('target_keyword','')} | タグ: {', '.join(selected_note.get('tags',[]))}")

                    rep_plat_sel = st.multiselect(
                        "生成するプラットフォーム",
                        PLATFORMS,
                        default=["x", "threads", "instagram"],
                        format_func=lambda p: f"{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}",
                        key="rep_note_plats",
                    )

                    if st.button("🚀 SNS投稿を一括生成", type="primary", key="rep_note_gen"):
                        if not rep_plat_sel:
                            st.error("プラットフォームを選択してください")
                        else:
                            topic = selected_note.get("target_keyword") or selected_note.get("title", "")
                            body = selected_note.get("body_outline", "")
                            category = selected_note.get("category", "")
                            extra = selected_note.get("tags", [])[:5]
                            source_title = selected_note["title"]
                            created_count = 0
                            for plat in rep_plat_sel:
                                result = format_post(plat, topic, body, category, extra, source_title)
                                post_title = f"{source_title[:30]} | {PLATFORM_LABELS[plat]}"
                                create_post(
                                    title=post_title,
                                    platform=plat,
                                    post_text=result["text"],
                                    hashtags=result["hashtags"],
                                    source_type="note",
                                    source_id=selected_note_id,
                                )
                                created_count += 1
                            st.success(f"✅ {created_count}プラットフォーム分の投稿を下書きとして保存しました！")
                            st.rerun()

                    # Preview generated content
                    if selected_note:
                        st.divider()
                        st.markdown("**プレビュー（現在の内容で生成）**")
                        topic_prev = selected_note.get("target_keyword") or selected_note.get("title", "")
                        body_prev = selected_note.get("body_outline", "")
                        cat_prev = selected_note.get("category", "")
                        extra_prev = selected_note.get("tags", [])[:5]
                        for plat in (rep_plat_sel or ["x"])[:3]:
                            result = format_post(plat, topic_prev, body_prev, cat_prev, extra_prev,
                                                  selected_note["title"])
                            with st.expander(f"{PLATFORM_ICONS[plat]} {PLATFORM_LABELS[plat]} プレビュー"):
                                st.text_area("", value=result["text"], height=120,
                                              key=f"note_prev_{plat}", disabled=True)

    # ── Video episodes ─────────────────────────────────────────────────────────
    with rep_tab_video:
        project_dir = ROOT / "project"
        if not project_dir.exists():
            st.info("project/ フォルダが見つかりません。")
        else:
            episodes = []
            for ep_dir in project_dir.iterdir():
                if ep_dir.is_dir():
                    ep_file = ep_dir / "episode.json"
                    if ep_file.exists():
                        try:
                            ep = json.loads(ep_file.read_text(encoding="utf-8"))
                            ep["_dir"] = ep_dir.name
                            episodes.append(ep)
                        except Exception:
                            pass

            if not episodes:
                st.info("エピソードが見つかりません。AI動画工場でエピソードを作成してください。")
                st.page_link("pages/5_Episode.py", label="🎬 エピソード管理を開く →")
            else:
                ep_options = {
                    f"{ep.get('_dir', '')} — {ep.get('title', ep.get('theme', '無題'))}": ep
                    for ep in episodes
                }
                selected_ep_label = st.selectbox("転用元エピソード", list(ep_options.keys()), key="rep_ep_sel")
                selected_ep = ep_options[selected_ep_label]

                ep_title = selected_ep.get("title") or selected_ep.get("theme", "")
                st.markdown(f"**テーマ:** {ep_title}")
                if selected_ep.get("character"):
                    st.caption(f"キャラクター: {selected_ep['character']}")

                video_plat_sel = st.multiselect(
                    "生成するプラットフォーム",
                    PLATFORMS,
                    default=["youtube_shorts", "x", "instagram"],
                    format_func=lambda p: f"{PLATFORM_ICONS[p]} {PLATFORM_LABELS[p]}",
                    key="rep_ep_plats",
                )

                if st.button("🚀 SNS投稿を一括生成", type="primary", key="rep_ep_gen"):
                    if not video_plat_sel:
                        st.error("プラットフォームを選択してください")
                    else:
                        topic = ep_title
                        extra = []
                        if selected_ep.get("character"):
                            extra.append(selected_ep["character"])
                        source_title = ep_title
                        created_count = 0
                        for plat in video_plat_sel:
                            result = format_post(plat, topic, "", "動画", extra, source_title)
                            create_post(
                                title=f"{ep_title[:30]} | {PLATFORM_LABELS[plat]}",
                                platform=plat,
                                post_text=result["text"],
                                hashtags=result["hashtags"],
                                source_type="video",
                                source_id=selected_ep.get("_dir"),
                            )
                            created_count += 1
                        st.success(f"✅ {created_count}プラットフォーム分の投稿を下書きとして保存しました！")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ANALYTICS (PLACEHOLDER)
# ══════════════════════════════════════════════════════════════════════════════

with tab_analytics:
    st.subheader("📈 SNS 分析")
    st.caption("外部APIと連携することで詳細な分析が可能になります。現在はプレースホルダーです。")

    # Manual engagement summary from local data
    st.markdown("**ローカル集計データ（手動入力ベース）**")
    all_posts = data.get("posts", [])
    published_posts = [p for p in all_posts if p.get("status") == "published"]

    if published_posts:
        total_likes = sum(p.get("engagement", {}).get("likes", 0) for p in published_posts)
        total_comments = sum(p.get("engagement", {}).get("comments", 0) for p in published_posts)
        total_shares = sum(p.get("engagement", {}).get("shares", 0) for p in published_posts)
        total_reach = sum(p.get("engagement", {}).get("reach", 0) for p in published_posts)

        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("❤️ 総いいね数", total_likes)
        ac2.metric("💬 総コメント数", total_comments)
        ac3.metric("🔁 総シェア数", total_shares)
        ac4.metric("👁️ 総リーチ", total_reach)

        st.divider()

        # Top posts by engagement
        top_posts = sorted(
            published_posts,
            key=lambda p: sum(p.get("engagement", {}).get(k, 0) for k in ("likes", "comments", "shares")),
            reverse=True,
        )[:5]

        st.subheader("🏆 エンゲージメントTop 5")
        for rank, post in enumerate(top_posts, 1):
            eng = post.get("engagement", {})
            total = eng.get("likes", 0) + eng.get("comments", 0) + eng.get("shares", 0)
            plat = post.get("platform", "x")
            tc1, tc2, tc3, tc4 = st.columns([1, 5, 2, 2])
            tc1.markdown(f"**#{rank}**")
            tc2.markdown(f"{PLATFORM_ICONS[plat]} {post.get('title', '無題')}")
            tc3.caption(post.get("published_date", ""))
            tc4.metric("", total)
    else:
        st.info("公開済み投稿がありません。投稿を公開するとデータが表示されます。")

    st.divider()

    # API integration status
    st.subheader("🔌 API 連携ステータス")
    analytics_status = get_analytics_status({})
    for key, info in analytics_status.items():
        with st.container(border=True):
            ac1, ac2 = st.columns([4, 1])
            with ac1:
                st.markdown(f"**{info['label']}**")
                st.caption(info["description"])
            with ac2:
                if info["status"] == "coming_soon":
                    st.info("🚧 Soon")
                else:
                    st.warning("📋 Stub")

    st.divider()
    st.subheader("📊 分析ロードマップ")
    st.markdown("""
| 機能 | バージョン | 説明 |
|------|-----------|------|
| X Analytics | v4.6 | X API v2でインプレッション・エンゲージメント取得 |
| Instagram Insights | v4.7 | Meta Graph APIでリーチ・フォロワー増減 |
| YouTube Analytics | v4.8 | 再生数・視聴維持率・クリック率 |
| 統合ダッシュボード | v5.0 | 全プラットフォーム横断分析 |
""")
