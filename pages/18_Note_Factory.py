"""
note投稿工場 — Creator Factory OS v4.3
Article management: draft → review → schedule → publish → archive
Scoring, revenue tracking, content repurposing, integration placeholders.
No external API calls.
"""
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.factories.note.article_manager import (
    load_articles, create_article, update_article, delete_article,
    transition_status, get_articles_by_status, get_factory_summary,
    STATUSES, STATUS_LABELS, STATUS_ICONS, TRANSITIONS,
)
from src.factories.note.article_scorer import (
    score_article, score_and_save, get_score_tips,
    CRITERIA, CRITERIA_LABELS, CRITERIA_ICONS, CRITERIA_DESCRIPTIONS,
)
from src.factories.note.revenue_tracker import (
    update_revenue, get_revenue_summary, get_article_revenue_rows,
)
from src.factories.note.repurpose_engine import (
    generate_all, generate_x_post, generate_threads_post,
    generate_youtube_shorts_script, generate_video_episode_proposal,
    save_repurpose,
)
from src.factories.note.integration_bridge import get_integration_status

APP_VERSION = "4.3"
TODAY = date.today()

st.set_page_config(page_title="note投稿工場 | Creator Factory OS", page_icon="📝", layout="wide")

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("📝 note投稿工場")
st.caption(f"コンテンツ制作・管理・収益化 | Creator Factory OS v{APP_VERSION} — Note Factory")

# ── Load data ──────────────────────────────────────────────────────────────────

data = load_articles()
summary = get_factory_summary(data)
articles = data.get("articles", [])

# Top-level metrics
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("📄 下書き", summary["draft"])
m2.metric("🔍 レビュー中", summary["reviewing"])
m3.metric("🗓️ スケジュール済", summary["scheduled"])
m4.metric("✅ 公開済", summary["published"])
m5.metric("📦 アーカイブ", summary["archived"])

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_dash, tab_manage, tab_score, tab_revenue, tab_repurpose, tab_integration = st.tabs([
    "📊 ダッシュボード",
    "📝 記事管理",
    "⭐ スコア分析",
    "💰 収益管理",
    "♻️ コンテンツ転用",
    "🔌 連携設定",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_dash:
    st.subheader("📊 Note ダッシュボード")

    by_status = get_articles_by_status(data)
    rev_summary = get_revenue_summary(data)

    # Revenue quick metrics
    rv1, rv2, rv3, rv4 = st.columns(4)
    rv1.metric("今日公開", summary["published_today"])
    rv2.metric("今月収益", f"¥{rev_summary['month_revenue']:,}")
    rv3.metric("累計実績収益", f"¥{rev_summary['total_actual_revenue']:,}")
    rv4.metric("総閲覧数", f"{rev_summary['total_views']:,}")

    st.divider()

    # Status columns
    STATUS_ORDER_DISPLAY = ["draft", "reviewing", "scheduled", "published", "archived"]
    col_list = st.columns(5)

    for col, status in zip(col_list, STATUS_ORDER_DISPLAY):
        icon = STATUS_ICONS[status]
        label = STATUS_LABELS[status]
        status_articles = by_status[status]
        with col:
            st.markdown(f"**{icon} {label}** ({len(status_articles)})")
            st.divider()
            if not status_articles:
                st.caption("なし")
            for art in status_articles:
                score_total = (art.get("score") or {}).get("total")
                score_badge = f" ⭐{score_total}" if score_total is not None else ""
                price_badge = f" ¥{art['price']:,}" if art.get("price", 0) > 0 else ""
                with st.container(border=True):
                    st.caption(f"**{art['title'][:28]}{'…' if len(art['title'])>28 else ''}**{score_badge}{price_badge}")
                    if art.get("published_at"):
                        st.caption(f"📅 {art['published_at']}")
                    if art.get("note_url"):
                        st.caption(f"🔗 [note]({art['note_url']})")

    st.divider()

    # Monthly calendar view
    st.subheader("📅 今月の公開カレンダー")
    month_prefix = TODAY.strftime("%Y-%m")
    this_month_published = [
        a for a in by_status["published"]
        if (a.get("published_at") or "")[:7] == month_prefix
    ]
    this_month_scheduled = [
        a for a in by_status["scheduled"]
        if (a.get("scheduled_at") or "")[:7] == month_prefix
    ]

    if not this_month_published and not this_month_scheduled:
        st.info("今月の公開・スケジュール記事はありません。")
    else:
        for a in sorted(this_month_published, key=lambda x: x.get("published_at", ""), reverse=True):
            st.success(f"✅ {a.get('published_at','')} — {a['title']}")
        for a in sorted(this_month_scheduled, key=lambda x: x.get("scheduled_at", ""), reverse=True):
            st.info(f"🗓️ {a.get('scheduled_at','')} 予定 — {a['title']}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ARTICLE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

with tab_manage:
    st.subheader("📝 記事管理")

    # ── New article form ───────────────────────────────────────────────────────
    with st.expander("➕ 新しい記事を作成", expanded=(len(articles) == 0)):
        with st.form("new_article_form", clear_on_submit=True):
            nc1, nc2 = st.columns([3, 1])
            with nc1:
                new_title = st.text_input("タイトル *", placeholder="例: AIで毎日コンテンツを量産する方法")
                new_keyword = st.text_input("ターゲットキーワード", placeholder="例: コンテンツ自動化")
            with nc2:
                new_category = st.text_input("カテゴリ", placeholder="例: 技術・ツール")
                new_read_time = st.number_input("推定読了時間 (分)", min_value=1, max_value=60, value=5)

            new_tags_str = st.text_input("タグ (カンマ区切り)", placeholder="例: AI, Python, 自動化")
            new_outline = st.text_area(
                "本文アウトライン",
                placeholder="## はじめに\nなぜこのテーマを書くのか？\n\n## 本論\n- ポイント1\n- ポイント2\n\n## まとめ",
                height=180,
            )
            new_price = st.number_input("価格 (円) ※ 0=無料", min_value=0, step=100, value=0)

            if st.form_submit_button("📝 記事を作成", type="primary"):
                if not new_title.strip():
                    st.error("タイトルを入力してください")
                else:
                    tags_list = [t.strip() for t in new_tags_str.split(",") if t.strip()]
                    create_article(
                        title=new_title.strip(),
                        category=new_category.strip(),
                        tags=tags_list,
                        target_keyword=new_keyword.strip(),
                        body_outline=new_outline.strip(),
                        estimated_read_time=new_read_time,
                        price=new_price,
                    )
                    st.success(f"✅ 記事「{new_title}」を作成しました")
                    st.rerun()

    # ── Status filter ──────────────────────────────────────────────────────────
    filter_status = st.selectbox(
        "ステータスで絞り込み",
        ["すべて"] + [STATUS_LABELS[s] for s in STATUSES],
        key="manage_filter",
    )
    status_filter_key = None
    if filter_status != "すべて":
        status_filter_key = next(s for s in STATUSES if STATUS_LABELS[s] == filter_status)

    filtered_articles = [
        a for a in articles
        if status_filter_key is None or a.get("status") == status_filter_key
    ]
    st.caption(f"{len(filtered_articles)} / {len(articles)} 件")

    # ── Article cards ──────────────────────────────────────────────────────────
    for art in sorted(filtered_articles, key=lambda a: a.get("updated_at", ""), reverse=True):
        art_id = art["id"]
        status = art.get("status", "draft")
        icon = STATUS_ICONS[status]
        label = STATUS_LABELS[status]
        score_info = art.get("score")
        score_badge = f" | ⭐ {score_info['total']}/100 ({score_info['grade']})" if score_info else ""

        with st.expander(
            f"{icon} {art['title']}  [{label}]{score_badge}",
            expanded=False,
        ):
            ec1, ec2 = st.columns([3, 2])

            with ec1:
                # Edit form
                with st.form(f"edit_{art_id}", clear_on_submit=False):
                    e_title = st.text_input("タイトル", value=art.get("title", ""), key=f"et_{art_id}")
                    e_keyword = st.text_input("キーワード", value=art.get("target_keyword", ""), key=f"ek_{art_id}")
                    e_cat = st.text_input("カテゴリ", value=art.get("category", ""), key=f"ec_{art_id}")
                    e_tags = st.text_input(
                        "タグ", value=", ".join(art.get("tags", [])), key=f"etg_{art_id}"
                    )
                    e_read = st.number_input("読了時間(分)", min_value=1, max_value=60,
                                             value=art.get("estimated_read_time", 5), key=f"er_{art_id}")
                    e_outline = st.text_area("アウトライン", value=art.get("body_outline", ""),
                                             height=150, key=f"eo_{art_id}")
                    e_price = st.number_input("価格", min_value=0, step=100,
                                              value=art.get("price", 0), key=f"ep_{art_id}")
                    e_url = st.text_input("noteURL", value=art.get("note_url") or "",
                                          key=f"eu_{art_id}")

                    if st.form_submit_button("💾 保存"):
                        tags_list = [t.strip() for t in e_tags.split(",") if t.strip()]
                        update_article(
                            art_id,
                            title=e_title,
                            target_keyword=e_keyword,
                            category=e_cat,
                            tags=tags_list,
                            estimated_read_time=e_read,
                            body_outline=e_outline,
                            price=e_price,
                            note_url=e_url or None,
                        )
                        st.success("保存しました")
                        st.rerun()

            with ec2:
                st.markdown("**ステータス変更**")
                st.caption(f"現在: {icon} {label}")
                allowed = TRANSITIONS.get(status, [])
                for next_status in allowed:
                    btn_label = f"{STATUS_ICONS[next_status]} → {STATUS_LABELS[next_status]}"
                    btn_type = "primary" if next_status == "published" else "secondary"
                    if st.button(btn_label, key=f"trans_{art_id}_{next_status}",
                                 use_container_width=True, type=btn_type):
                        note_url_val = ""
                        if next_status == "published":
                            note_url_val = art.get("note_url") or ""
                        ok, msg, _ = transition_status(art_id, next_status, note_url_val)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                        st.rerun()

                st.divider()
                st.markdown("**情報**")
                st.caption(f"作成: {art.get('created_at', '')}")
                st.caption(f"更新: {art.get('updated_at', '')}")
                if art.get("published_at"):
                    st.caption(f"公開: {art['published_at']}")

                st.divider()
                if st.button("🗑️ 削除", key=f"del_{art_id}", use_container_width=True):
                    st.session_state[f"confirm_del_{art_id}"] = True

                if st.session_state.get(f"confirm_del_{art_id}"):
                    st.warning("本当に削除しますか？")
                    dc1, dc2 = st.columns(2)
                    if dc1.button("削除する", key=f"del_yes_{art_id}", type="primary"):
                        delete_article(art_id)
                        st.session_state.pop(f"confirm_del_{art_id}", None)
                        st.rerun()
                    if dc2.button("キャンセル", key=f"del_no_{art_id}"):
                        st.session_state.pop(f"confirm_del_{art_id}", None)
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCORE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab_score:
    st.subheader("⭐ スコア分析")
    st.caption("6つの基準で記事をスコアリングします。外部API不要・ルールベース。")

    if not articles:
        st.info("記事がありません。「記事管理」タブで作成してください。")
        st.stop()

    # Batch score all
    sc1, sc2 = st.columns([3, 1])
    with sc2:
        if st.button("🔄 全記事を再スコア", use_container_width=True):
            for art in articles:
                score_and_save(art["id"])
            st.success("全記事をスコアリングしました")
            st.rerun()

    # Article selector
    art_options = {f"{STATUS_ICONS[a.get('status','draft')]} {a['title']}": a["id"] for a in articles}
    selected_label = st.selectbox("記事を選択", list(art_options.keys()), key="score_select")
    selected_id = art_options[selected_label]

    # Reload to get current state
    data_fresh = load_articles()
    selected_art = next((a for a in data_fresh.get("articles", []) if a["id"] == selected_id), None)

    if not selected_art:
        st.error("記事が見つかりません")
        st.stop()

    col_btn, col_tip = st.columns([1, 3])
    with col_btn:
        if st.button("⭐ スコアを計算", type="primary", use_container_width=True, key="score_now"):
            score_and_save(selected_id)
            st.rerun()

    score_data = selected_art.get("score")
    if not score_data:
        st.info("「⭐ スコアを計算」ボタンを押してください。")
    else:
        scores = score_data.get("scores", {})
        total = score_data.get("total", 0)
        grade = score_data.get("grade", "D")
        scored_at = score_data.get("scored_at", "")

        grade_colors = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📉"}
        st.markdown(f"### 総合スコア: **{total} / 100** — {grade_colors.get(grade, '')} グレード **{grade}**")
        st.progress(total / 100)
        st.caption(f"スコア計算日: {scored_at}")

        st.divider()

        # Criteria breakdown
        score_cols = st.columns(3)
        for i, criterion in enumerate(CRITERIA):
            val = scores.get(criterion, 0)
            icon = CRITERIA_ICONS[criterion]
            label = CRITERIA_LABELS[criterion]
            desc = CRITERIA_DESCRIPTIONS[criterion]
            with score_cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{icon} {label}**")
                    st.caption(desc)
                    st.progress(val / 20, text=f"{val} / 20")

        st.divider()

        # Improvement tips
        tips = get_score_tips(score_data)
        if tips:
            st.subheader("💡 改善アドバイス")
            for tip in tips:
                st.markdown(f"- {tip}")
        else:
            st.success("✅ すべての基準で高スコアです！")

    st.divider()

    # Score leaderboard
    st.subheader("📊 スコアランキング")
    scored_articles = [a for a in articles if a.get("score")]
    if scored_articles:
        scored_articles.sort(key=lambda a: a["score"]["total"], reverse=True)
        for rank, art in enumerate(scored_articles, 1):
            sc_info = art["score"]
            grade_icon = {"S": "🏆", "A": "🥇", "B": "🥈", "C": "🥉", "D": "📉"}.get(sc_info["grade"], "")
            rc = st.columns([1, 5, 2, 2])
            rc[0].metric("", f"#{rank}")
            rc[1].markdown(f"{STATUS_ICONS.get(art.get('status','draft'),'📄')} {art['title']}")
            rc[2].metric("スコア", f"{sc_info['total']}/100")
            rc[3].metric("グレード", f"{grade_icon} {sc_info['grade']}")
    else:
        st.info("スコア済み記事がありません。上で各記事をスコアリングしてください。")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — REVENUE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

with tab_revenue:
    st.subheader("💰 収益管理")

    data_rev = load_articles()
    rev_sum = get_revenue_summary(data_rev)

    # Summary metrics
    rv1, rv2, rv3, rv4, rv5, rv6 = st.columns(6)
    rv1.metric("公開記事数", rev_sum["total_articles"])
    rv2.metric("有料記事数", rev_sum["paid_articles"])
    rv3.metric("想定収益合計", f"¥{rev_sum['total_estimated_revenue']:,}")
    rv4.metric("実績収益合計", f"¥{rev_sum['total_actual_revenue']:,}")
    rv5.metric("累計販売数", rev_sum["total_sales"])
    rv6.metric("累計閲覧数", f"{rev_sum['total_views']:,}")

    if rev_sum.get("top_earner"):
        te = rev_sum["top_earner"]
        st.success(f"🏆 トップ記事: 「{te['title']}」 — 実績 ¥{te.get('actual_revenue',0):,}")

    st.divider()

    # Per-article revenue editor
    st.subheader("📋 記事別収益データ")

    revenue_rows = get_article_revenue_rows(data_rev)
    if not revenue_rows:
        st.info("公開済みまたはアーカイブ済みの記事がありません。")
    else:
        for row in revenue_rows:
            with st.expander(
                f"{'✅' if row['status']=='published' else '📦'} {row['title']} — ¥{row['actual_revenue']:,}",
                expanded=False,
            ):
                rc1, rc2, rc3 = st.columns(3)
                with rc1:
                    st.caption(f"**公開日:** {row['published_at']}")
                    if row["note_url"]:
                        st.caption(f"**URL:** [{row['note_url'][:40]}]({row['note_url']})")
                    est = row["price"] * row["sales_count"]
                    st.metric("想定収益", f"¥{est:,}")
                with rc2:
                    with st.form(f"rev_{row['id']}"):
                        new_price = st.number_input("価格 (円)", min_value=0, step=100,
                                                     value=row["price"], key=f"rp_{row['id']}")
                        new_sales = st.number_input("販売数", min_value=0, value=row["sales_count"],
                                                     key=f"rs_{row['id']}")
                        new_actual = st.number_input("実績収益 (円)", min_value=0, step=100,
                                                      value=row["actual_revenue"], key=f"ra_{row['id']}")
                        if st.form_submit_button("💾 保存"):
                            update_revenue(row["id"], price=new_price, sales_count=new_sales,
                                           actual_revenue=new_actual)
                            st.success("保存しました")
                            st.rerun()
                with rc3:
                    with st.form(f"rev_stat_{row['id']}"):
                        new_views = st.number_input("閲覧数", min_value=0,
                                                     value=row["view_count"], key=f"rv_{row['id']}")
                        new_likes = st.number_input("スキ数", min_value=0,
                                                     value=row["like_count"], key=f"rl_{row['id']}")
                        if st.form_submit_button("💾 保存"):
                            update_revenue(row["id"], view_count=new_views, like_count=new_likes)
                            st.success("保存しました")
                            st.rerun()

    st.divider()
    st.subheader("📈 収益シミュレーション")
    sim_c1, sim_c2 = st.columns(2)
    with sim_c1:
        sim_price = st.number_input("想定販売価格 (円)", min_value=0, value=500, step=100, key="sim_price")
        sim_articles = st.number_input("月間公開記事数", min_value=1, value=4, key="sim_articles")
    with sim_c2:
        sim_sales_per = st.number_input("1記事あたり想定販売数", min_value=0, value=10, key="sim_sales")
        sim_free_views = st.number_input("無料記事の月間想定閲覧数", min_value=0, value=500, key="sim_views")

    sim_monthly = sim_price * sim_sales_per * sim_articles
    sim_annual = sim_monthly * 12
    st.info(
        f"📊 試算: 月収 **¥{sim_monthly:,}** / 年収 **¥{sim_annual:,}**  "
        f"（有料{sim_articles}記事 × {sim_sales_per}販売/記事 × ¥{sim_price:,}）"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — CONTENT REPURPOSING
# ══════════════════════════════════════════════════════════════════════════════

with tab_repurpose:
    st.subheader("♻️ コンテンツ転用")
    st.caption("記事を X・Threads・YouTube Shorts・動画エピソードに展開します。外部API不要。")

    if not articles:
        st.info("記事がありません。「記事管理」タブで作成してください。")
        st.stop()

    rep_options = {f"{STATUS_ICONS[a.get('status','draft')]} {a['title']}": a["id"] for a in articles}
    rep_label = st.selectbox("転用元記事を選択", list(rep_options.keys()), key="rep_select")
    rep_id = rep_options[rep_label]

    data_rep = load_articles()
    rep_art = next((a for a in data_rep.get("articles", []) if a["id"] == rep_id), None)

    if not rep_art:
        st.error("記事が見つかりません")
        st.stop()

    st.divider()

    # Generate all button
    gen_col1, gen_col2 = st.columns([2, 3])
    with gen_col1:
        if st.button("🚀 全フォーマットを一括生成", type="primary", use_container_width=True, key="gen_all"):
            rep_data = generate_all(rep_art)
            save_repurpose(rep_id, rep_data)
            st.success("✅ 全フォーマットを生成・保存しました")
            st.rerun()
    with gen_col2:
        existing = rep_art.get("repurpose", {})
        if existing.get("generated_at"):
            st.caption(f"最終生成: {existing['generated_at']}")

    existing_repurpose = rep_art.get("repurpose", {})

    # X post
    with st.expander("𝕏 X版 (Twitter)", expanded=True):
        xc1, xc2 = st.columns([4, 1])
        with xc2:
            if st.button("生成", key="gen_x", use_container_width=True):
                x_text = generate_x_post(rep_art)
                data_upd = load_articles()
                for a in data_upd.get("articles", []):
                    if a["id"] == rep_id:
                        a.setdefault("repurpose", {})["x_post"] = x_text
                        break
                from src.factories.note.article_manager import save_articles
                save_articles(data_upd)
                st.rerun()
        x_content = existing_repurpose.get("x_post") or ""
        if x_content:
            x_edited = st.text_area("X投稿テキスト", value=x_content, height=160, key="x_edit")
            char_count = len(x_edited)
            col_cnt, col_copy = st.columns([3, 1])
            col_cnt.caption(f"{char_count} / 280 文字 {'⚠️ 超過' if char_count > 280 else '✅'}")
        else:
            st.caption("「生成」ボタンを押してください")

    # Threads
    with st.expander("🧵 Threads版"):
        tc1, tc2 = st.columns([4, 1])
        with tc2:
            if st.button("生成", key="gen_threads", use_container_width=True):
                threads_text = generate_threads_post(rep_art)
                data_upd = load_articles()
                for a in data_upd.get("articles", []):
                    if a["id"] == rep_id:
                        a.setdefault("repurpose", {})["threads_post"] = threads_text
                        break
                from src.factories.note.article_manager import save_articles
                save_articles(data_upd)
                st.rerun()
        threads_content = existing_repurpose.get("threads_post") or ""
        if threads_content:
            st.text_area("Threads投稿テキスト", value=threads_content, height=200, key="threads_edit")
        else:
            st.caption("「生成」ボタンを押してください")

    # YouTube Shorts
    with st.expander("🎬 YouTube Shortsスクリプト"):
        yc1, yc2 = st.columns([4, 1])
        with yc2:
            if st.button("生成", key="gen_yt", use_container_width=True):
                yt_text = generate_youtube_shorts_script(rep_art)
                data_upd = load_articles()
                for a in data_upd.get("articles", []):
                    if a["id"] == rep_id:
                        a.setdefault("repurpose", {})["youtube_shorts_script"] = yt_text
                        break
                from src.factories.note.article_manager import save_articles
                save_articles(data_upd)
                st.rerun()
        yt_content = existing_repurpose.get("youtube_shorts_script") or ""
        if yt_content:
            st.text_area("Shortsスクリプト", value=yt_content, height=300, key="yt_edit")
            st.download_button(
                "⬇️ スクリプトをダウンロード",
                data=yt_content.encode("utf-8"),
                file_name=f"{rep_id}_shorts_script.md",
                mime="text/markdown",
                key="yt_dl",
            )
        else:
            st.caption("「生成」ボタンを押してください")

    # Video episode proposal
    with st.expander("🎥 動画エピソード提案 (AI動画工場連携)"):
        vc1, vc2 = st.columns([4, 1])
        with vc2:
            if st.button("生成", key="gen_vid", use_container_width=True):
                vid_text = generate_video_episode_proposal(rep_art)
                data_upd = load_articles()
                for a in data_upd.get("articles", []):
                    if a["id"] == rep_id:
                        a.setdefault("repurpose", {})["video_episode_proposal"] = vid_text
                        break
                from src.factories.note.article_manager import save_articles
                save_articles(data_upd)
                st.rerun()
        vid_content = existing_repurpose.get("video_episode_proposal") or ""
        if vid_content:
            st.markdown(vid_content)
            st.page_link("pages/6_Produce.py", label="→ AI動画工場の一発生成を開く", icon="🎬")
        else:
            st.caption("「生成」ボタンを押してください")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — INTEGRATION SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

with tab_integration:
    st.subheader("🔌 連携設定")
    st.caption("外部サービスとの連携設定です。現時点では実装準備のみ。APIは呼び出しません。")

    data_int = load_articles()
    int_config = data_int.get("integration", {})
    int_status = get_integration_status(int_config)

    # Status overview
    for key, info in int_status.items():
        with st.container(border=True):
            ic1, ic2, ic3 = st.columns([3, 2, 1])
            with ic1:
                st.markdown(f"**{info['label']}**")
                st.caption(info["description"])
            with ic2:
                if info["status"] == "coming_soon":
                    st.info("🚧 Coming Soon")
                else:
                    st.warning("📋 Placeholder")
            with ic3:
                cfg_icon = "✅" if info["configured"] else "⬜"
                st.caption(f"設定: {cfg_icon}")

    st.divider()

    # Config form (stores values but doesn't activate)
    with st.expander("🔧 接続設定 (将来の統合に備えて保存)", expanded=False):
        with st.form("integration_form"):
            int_api_key = st.text_input(
                "note API Key (将来対応)",
                value=int_config.get("note_api_key") or "",
                type="password",
                disabled=True,
                help="note公式APIが公開された際に使用します",
            )
            int_rss = st.text_input(
                "RSS Feed URL",
                value=int_config.get("rss_url") or "",
                placeholder="https://note.com/username/rss",
                disabled=True,
            )
            int_analytics = st.text_input(
                "Analytics ID",
                value=int_config.get("analytics_id") or "",
                placeholder="G-XXXXXXXXXX",
                disabled=True,
            )
            st.caption("⚠️ 現在これらの設定はプレースホルダーです。外部API接続は行いません。")
            if st.form_submit_button("💾 保存 (設定のみ)", disabled=True):
                pass

    st.divider()
    st.subheader("📋 統合ロードマップ")
    st.markdown("""
| 統合 | バージョン | 説明 |
|------|-----------|------|
| note API | v5.0 | note公式APIが公開次第、自動投稿・統計取得に対応 |
| RSS モニタリング | v4.6 | RSSでコメント・リアクションを監視 |
| Analytics | v4.9 | Google Analyticsとのトラフィック統合 |
| SNS自動投稿 | v4.4 | note公開時にX・Threadsへ自動投稿 |
| 動画連動 | v4.9 | note記事から動画エピソードを自動提案 |
""")
