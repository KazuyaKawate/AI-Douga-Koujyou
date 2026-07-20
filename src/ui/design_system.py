from __future__ import annotations

import html

import streamlit as st


DESIGN_SYSTEM_NAME = "AIOS Design System v8"
THEME_NAME = "Calm Revenue Command Center"

NEON_COMPONENTS = (
    "NeonPanel", "NeonCard", "NeonHeader", "NeonBadge", "NeonMetric",
    "NeonButton", "NeonDisabledButton", "NeonInputFrame", "NeonTimeline",
    "NeonFlowLine", "NeonStatusIndicator", "SingularityCore",
    "StarfieldBackground", "NeonToolbar", "NeonNavigation", "NeonModal",
    "NeonTable", "NeonEmptyState", "NeonWarning", "NeonReviewRequired",
)


AIOS_DESIGN_SYSTEM_CSS = r"""
<style>
:root{
  color-scheme:light;
  --aios-brand-primary:#237A78;--aios-brand-secondary:#5576A5;--aios-brand-accent:#8A78A6;--aios-brand-warm:#D7A86E;
  --aios-bg-deepest:#F4F8F7;--aios-bg-deep:var(--aios-bg-deepest);--aios-bg-cosmic-start:#EEF6F5;--aios-bg-cosmic-end:#F4F1F8;
  --aios-neon-cyan:var(--aios-brand-primary);--aios-neon-magenta:var(--aios-brand-accent);--aios-neon-pink:#B45F78;
  --aios-text-primary:#203335;--aios-text-secondary:#536668;--aios-text-subtle-cyan:#356F70;--aios-text-cyan-muted:var(--aios-text-subtle-cyan);
  --aios-panel-bg:rgba(255,255,255,.88);--aios-panel-bg-strong:rgba(255,255,255,.96);--aios-surface-1:#FFFFFF;--aios-surface-2:#F1F6F5;
  --aios-panel-border-cyan:rgba(35,122,120,.22);--aios-panel-border-magenta:rgba(138,120,166,.24);--aios-border-cyan:var(--aios-panel-border-cyan);--aios-border-magenta:var(--aios-panel-border-magenta);
  --aios-glow-cyan-sm:0 2px 10px rgba(35,122,120,.08);--aios-glow-cyan-md:0 8px 24px rgba(35,122,120,.10);--aios-glow-cyan-lg:0 14px 34px rgba(35,122,120,.12);
  --aios-glow-magenta-sm:0 2px 10px rgba(138,120,166,.08);--aios-glow-magenta-md:0 8px 24px rgba(138,120,166,.10);--aios-glow-magenta-lg:0 14px 34px rgba(138,120,166,.12);
  --aios-glow-low:0 3px 14px rgba(49,77,78,.07);--aios-glow-medium:0 8px 28px rgba(49,77,78,.10);--aios-glow-high:0 14px 38px rgba(49,77,78,.13);
  --aios-radius-sm:10px;--aios-radius-md:16px;--aios-radius-lg:24px;
  --aios-transition-fast:140ms ease;--aios-transition-base:240ms ease;--aios-transition-slow:520ms ease;
  --aios-space-xs:.35rem;--aios-space-sm:.65rem;--aios-space-md:1rem;--aios-space-lg:1.5rem;
  --aios-status-success:#2F7D5C;--aios-status-warning:#946A22;--aios-status-danger:#A94455;
  --aios-status-review:#705887;--aios-status-dryrun:#276F82;
  --aios-font:"Inter","Montserrat","Noto Sans JP","Yu Gothic UI",system-ui,sans-serif;
  --aios-breakpoint-mobile:720px;
}
html,body,[class*="css"],.stApp{font-family:var(--aios-font);color:var(--aios-text-primary)}
.stApp{background-color:var(--aios-bg-deepest);background-image:linear-gradient(145deg,#F7FAF9 0%,#EEF6F5 48%,#F4F1F8 100%);background-attachment:fixed;overflow-x:clip}
[data-testid="stHeader"]{background:rgba(247,250,249,.92);border-bottom:1px solid var(--aios-border-cyan);backdrop-filter:blur(14px)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#F8FBFA,#EDF4F3);border-right:1px solid var(--aios-border-cyan)}
.block-container{max-width:1200px;padding-top:1.25rem;padding-bottom:6rem}
h1,h2,h3,h4,strong,label{color:var(--aios-text-primary)}p,small,.stCaption{color:var(--aios-text-secondary)}
a{color:var(--aios-text-cyan-muted)}
.aios-page-header,.aios-shell,.cmd-shell,.hub-card,.aios-glass,.aios-card,.cmd-card,.cmd-chat,.cmd-context,.aios-task,.neon-panel,.neon-card,.neon-modal,.neon-table,.neon-toolbar,.neon-navigation{background:linear-gradient(145deg,var(--aios-panel-bg-strong),var(--aios-surface-2));border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-md);box-shadow:var(--aios-glow-low)}
.neon-panel,.neon-card,.neon-modal,.neon-table,.neon-toolbar,.neon-navigation{padding:var(--aios-space-md)}
.neon-header,.neon-metric{color:var(--aios-text-primary)}.neon-badge,.neon-status-indicator{display:inline-flex;align-items:center;gap:.4rem;border:1px solid currentColor;border-radius:999px;padding:.35rem .7rem}.neon-metric{font-size:clamp(1.45rem,4vw,2rem);font-weight:800;color:var(--aios-neon-cyan)}
.neon-button,.neon-disabled-button{min-height:44px;border:1px solid var(--aios-neon-cyan);border-radius:var(--aios-radius-sm);padding:.55rem .9rem;color:#fff;background:rgba(0,255,255,.1)}.neon-disabled-button{cursor:not-allowed;filter:saturate(.25);box-shadow:none;color:#b8c4c4}
.neon-input-frame{border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-sm);background:var(--aios-panel-bg);padding:.5rem}.neon-timeline,.neon-flow-line{border-left:3px solid var(--aios-neon-cyan);filter:drop-shadow(0 0 5px rgba(0,255,255,.45));padding-left:1rem}
.neon-empty-state,.neon-warning,.neon-review-required{padding:var(--aios-space-md);border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-md);background:var(--aios-panel-bg)}.neon-warning{border-color:var(--aios-neon-pink)}.neon-review-required{border-color:var(--aios-neon-magenta)}
.singularity-core{width:clamp(22px,5vw,52px);aspect-ratio:1;border-radius:50%;background:var(--aios-brand-primary)}.starfield-background{display:none;pointer-events:none}.state-ready,.state-verified{color:var(--aios-status-success)}.state-warning,.state-proposal{color:var(--aios-status-review)}.state-blocked{color:var(--aios-status-danger)}.state-na{color:#738183}
@keyframes aios-soft-pulse{50%{opacity:.78;transform:scale(.96)}}
.aios-page-header{padding:var(--aios-space-lg);margin-bottom:var(--aios-space-md);position:relative;overflow:hidden}
.aios-page-header::before{content:"";position:absolute;inset:0 0 auto 0;height:2px;background:linear-gradient(90deg,var(--aios-neon-cyan),var(--aios-neon-magenta),var(--aios-neon-pink))}
.aios-eyebrow{margin:0;color:var(--aios-text-cyan-muted);font-size:.78rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}
.aios-page-header h1{margin:.3rem 0;font-size:clamp(1.75rem,4vw,2.7rem);color:var(--aios-text-primary)}
.aios-page-header p{margin:0;max-width:70ch}
.aios-status-strip,.hub-safe{display:flex;flex-wrap:wrap;gap:var(--aios-space-sm);margin:.7rem 0 1rem}
.aios-status,.aios-badge,.cmd-pill,.hub-safe>div{display:inline-flex;align-items:center;gap:.4rem;min-height:44px;padding:.4rem .75rem;border:1px solid var(--aios-border-cyan);border-radius:999px;background:rgba(255,255,255,.82);color:var(--aios-text-primary);font-size:.78rem;font-weight:800}
.aios-status::before{content:"●";font-size:.65rem}.aios-status--dryrun{color:var(--aios-status-dryrun)}.aios-status--review{color:var(--aios-status-review)}.aios-status--blocked,.aios-stop{color:var(--aios-status-warning)}
.aios-home-link{display:inline-flex;align-items:center;min-height:44px;padding:.45rem .75rem;margin:0 0 .65rem;border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-sm);background:#fff;color:var(--aios-text-primary);text-decoration:none}.aios-home-link:hover{border-color:var(--aios-brand-accent);box-shadow:var(--aios-glow-low)}
.aios-card,.cmd-card,.cmd-chat,.cmd-context,.aios-task,.hub-card{padding:var(--aios-space-md);margin-bottom:var(--aios-space-sm)}
.aios-card h4,.cmd-label,.aios-muted,.cmd-route{color:var(--aios-text-secondary)}
.aios-number,.cmd-number{font-size:clamp(1.55rem,4vw,2rem);font-weight:800;color:var(--aios-neon-cyan);text-shadow:0 0 12px rgba(0,255,255,.25)}
.cmd-user{border-left:3px solid var(--aios-neon-cyan)}.cmd-ai{border-left:3px solid var(--aios-neon-magenta)}
.cmd-command-deck{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.8rem 1rem;margin:.6rem 0 1rem;border:1px solid var(--aios-border-magenta);border-radius:var(--aios-radius-md);background:linear-gradient(100deg,rgba(0,255,255,.08),rgba(255,0,255,.13));box-shadow:var(--aios-glow-medium)}
.cmd-command-deck strong{color:var(--aios-neon-cyan)}.cmd-command-deck span{color:var(--aios-text-secondary);font-size:.82rem}
.aios-log{border-left:3px solid var(--aios-neon-cyan);padding:.3rem .7rem;color:var(--aios-text-secondary)}
.cmd-fixed-input,div.st-key-hub_action_bar{background:rgba(255,255,255,.96);border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-md);padding:.75rem;box-shadow:var(--aios-glow-medium)}
.cmd-fixed-input{position:sticky;bottom:.4rem;z-index:20}div.st-key-hub_action_bar{position:fixed;left:0;right:0;bottom:0;z-index:999;padding:.55rem max(.75rem,env(safe-area-inset-right)) calc(.55rem + env(safe-area-inset-bottom)) max(.75rem,env(safe-area-inset-left))}
[data-testid="stChatInput"]{position:sticky;bottom:0;z-index:50;background:rgba(255,255,255,.96);padding:.4rem 0 calc(.4rem + env(safe-area-inset-bottom));border-top:1px solid var(--aios-border-cyan)}[data-testid="stChatInput"] textarea{min-height:46px}[data-testid="stChatMessage"]{scroll-margin-bottom:6rem;border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-md);background:rgba(255,255,255,.78);margin:.45rem 0}
div.stButton>button,.stDownloadButton>button,[data-testid="stLinkButton"] a{min-height:46px;border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-sm);background:#fff;color:var(--aios-text-primary);font-weight:800;transition:border-color .16s ease,box-shadow .16s ease,transform .16s ease}
[data-testid^="stPageLink"],[data-testid^="stPageLink"] a,[data-testid="stSidebarNav"] a,[data-testid="stSidebar"] a{min-height:44px!important;display:flex;align-items:center;white-space:normal!important;line-height:1.35!important;padding-top:.55rem!important;padding-bottom:.55rem!important;overflow:visible!important;text-overflow:clip!important}
[data-testid^="stPageLink"] p,[data-testid="stSidebarNav"] p{white-space:normal!important;overflow:visible!important;text-overflow:clip!important;line-height:1.35!important}
[data-testid="stHeader"] button,[data-testid="stSidebarCollapseButton"] button,[data-testid="stSidebarCollapsedControl"] button{min-width:44px!important;min-height:44px!important}
[data-testid="stMainBlockContainer"] button{min-height:44px!important}
[data-testid="stMainBlockContainer"] a{min-height:44px!important;display:flex;align-items:center;white-space:normal!important;line-height:1.35!important;overflow:visible!important;text-overflow:clip!important}
[data-testid="stMainBlockContainer"] a p{white-space:normal!important;overflow:visible!important;text-overflow:clip!important;line-height:1.35!important}
div.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stLinkButton"] a:hover{border-color:var(--aios-neon-magenta);box-shadow:var(--aios-glow-medium);transform:translateY(-1px)}
div.stButton>button:disabled,.stDownloadButton>button:disabled{opacity:.58;filter:saturate(.2);cursor:not-allowed;box-shadow:none;transform:none}
div.stButton>button[kind="primary"]{background:linear-gradient(110deg,var(--aios-brand-primary),var(--aios-brand-secondary));border-color:var(--aios-brand-primary);color:#fff}
div.stButton>button:focus-visible,.stDownloadButton>button:focus-visible,a:focus-visible,input:focus-visible,textarea:focus-visible,[role="tab"]:focus-visible{outline:3px solid #fff!important;outline-offset:2px!important;box-shadow:0 0 0 5px rgba(0,255,255,.38)!important}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{background:#fff!important;color:var(--aios-text-primary)!important;border-color:var(--aios-border-cyan)!important;border-radius:var(--aios-radius-sm)!important}
[data-testid="stTextInput"] input,[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{min-height:44px!important}
[data-testid="stMetricLabel"]{overflow:visible!important}[data-testid="stMetricLabel"] p{white-space:normal!important;overflow:visible!important;text-overflow:clip!important}
[data-baseweb="tab-list"]{gap:.25rem;border-bottom:1px solid var(--aios-border-cyan)}[role="tab"]{color:var(--aios-text-secondary);min-height:44px}[aria-selected="true"]{color:var(--aios-neon-cyan)!important;border-bottom-color:var(--aios-neon-cyan)!important}
[data-testid="stAlert"]{border-radius:var(--aios-radius-md);border:1px solid currentColor;background:rgba(255,255,255,.7)}
[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,var(--aios-neon-cyan),var(--aios-neon-magenta))}
.aios-empty,.aios-loading,.aios-error,.aios-warning,.aios-approval{padding:var(--aios-space-md);border:1px solid var(--aios-border-cyan);border-radius:var(--aios-radius-md);background:var(--aios-surface-1)}
.aios-error{border-color:var(--aios-status-danger)}.aios-warning{border-color:var(--aios-status-warning)}.aios-approval{border-color:var(--aios-status-review)}
.hub-safe{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}.hub-safe>div{justify-content:center;text-align:center;border-radius:var(--aios-radius-md)}
.aios-state-legend{display:flex;flex-wrap:wrap;gap:.5rem;margin:.65rem 0 1rem}.aios-state-label{display:inline-flex;align-items:center;gap:.4rem;min-height:44px;padding:.45rem .75rem;border:1px solid currentColor;border-radius:999px;background:#fff;font-size:.78rem;font-weight:800}.aios-state-label::before{content:"●"}.aios-state-label.state-na::before{content:"○"}
.aios-mobile-nav{display:none}
pre,code{white-space:pre-wrap!important;overflow-wrap:anywhere;color:var(--aios-text-cyan-muted)!important}
@media(max-width:720px){.block-container{padding:.8rem .65rem 7rem;max-width:100%}.aios-page-header{padding:1rem}.hub-safe{grid-template-columns:1fr 1fr}.aios-card,.cmd-card{min-height:auto}.aios-number,.cmd-number{font-size:1.45rem}[data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.45rem}[data-testid="column"]{min-width:calc(50% - .45rem)!important;flex:1 1 calc(50% - .45rem)!important}div.st-key-hub_action_bar [data-testid="column"]{min-width:calc(33.333% - .45rem)!important;flex-basis:calc(33.333% - .45rem)!important}.cmd-fixed-input{bottom:4.2rem}[data-testid="stChatMessage"]{padding:.5rem .25rem}[data-testid="stChatInput"]{padding:.5rem 0 calc(4.8rem + env(safe-area-inset-bottom))}button,a{min-height:46px}img,svg,canvas,table{max-width:100%}.aios-mobile-nav{position:fixed;display:grid;grid-template-columns:repeat(4,1fr);left:.5rem;right:.5rem;bottom:calc(.45rem + env(safe-area-inset-bottom));z-index:1000;background:rgba(255,255,255,.96);border:1px solid var(--aios-border-cyan);border-radius:16px;box-shadow:var(--aios-glow-medium);overflow:hidden}.aios-mobile-nav a{display:flex;min-height:54px;align-items:center;justify-content:center;text-align:center;padding:.3rem;color:var(--aios-text-primary);font-size:.72rem;font-weight:800;text-decoration:none}.aios-mobile-nav a:hover{background:var(--aios-surface-2)}}
@media(max-width:480px){div.st-key-hub_action_bar{position:sticky;left:auto;right:auto;bottom:0}div.st-key-hub_action_bar [data-testid="column"]{min-width:100%!important;flex-basis:100%!important}.block-container{padding-bottom:2rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.01ms!important}.stApp{background-attachment:scroll}}
@media(max-width:720px){.cmd-command-deck{align-items:flex-start;flex-direction:column}}
</style>
"""


def apply_design_system() -> None:
    st.markdown(AIOS_DESIGN_SYSTEM_CSS, unsafe_allow_html=True)
    st.markdown(
        '<nav class="aios-mobile-nav" aria-label="AIOS mobile navigation">'
        '<a href="./Dashboard">ホーム</a>'
        '<a href="./Commander_Console">Commander</a>'
        '<a href="./Mobile_Review_Hub">レビュー</a>'
        '<a href="./Revenue_Engine">収益</a>'
        '</nav>',
        unsafe_allow_html=True,
    )
    try:
        st.sidebar.markdown("### AIOS")
        st.sidebar.page_link("pages/8_Dashboard.py", label="Dashboard", icon="🏠")
        st.sidebar.page_link("pages/45_Commander_Console.py", label="Commander", icon="💬")
        st.sidebar.page_link("pages/51_Mobile_Review_Hub.py", label="Mobile Review", icon="✅")
        st.sidebar.page_link("pages/38_Revenue_Engine.py", label="Revenue", icon="📈")
        st.sidebar.page_link("pages/47_Daily_Operation.py", label="Business Home", icon="🏢")
    except KeyError:
        st.sidebar.markdown('[🏠 Dashboard](./8_Dashboard)')


def business_home_link() -> None:
    """Render the canonical, non-mutating return route to Business Home."""
    st.markdown(
        '<a class="aios-home-link" href="./Daily_Operation" aria-label="Business Homeへ戻る">🏢 Business Homeへ戻る</a>',
        unsafe_allow_html=True,
    )


def neon_component(component: str, content: str = "", *, label: str | None = None) -> None:
    """Render a presentation-only v8 primitive; all input is HTML escaped."""
    if component not in NEON_COMPONENTS:
        raise ValueError(f"Unknown Design System v8 component: {component}")
    css_class = "".join(f"-{char.lower()}" if char.isupper() else char for char in component).lstrip("-")
    aria = f' aria-label="{html.escape(label)}"' if label else ""
    st.markdown(
        f'<section class="{css_class}"{aria}>{html.escape(content)}</section>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, *, eyebrow: str = "AIOS / CALM COMMAND CENTER") -> None:
    st.markdown(
        f'<header class="aios-page-header"><p class="aios-eyebrow">{html.escape(eyebrow)}</p><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></header>',
        unsafe_allow_html=True,
    )


def safety_status_strip() -> None:
    st.markdown(
        '<div class="aios-status-strip" aria-label="AIOS safety status">'
        '<span class="aios-status aios-status--dryrun">DryRun ON</span>'
        '<span class="aios-status aios-status--review">Approval Required</span>'
        '<span class="aios-status aios-status--blocked">Production Blocked</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def review_action_component(*, key_prefix: str = "review_action") -> str | None:
    """Render the shared three-step review action bar without production execution."""
    st.caption("1. 内容確認 → 2. 承認判断 → 3. 公開準備（手動）")
    c1, c2, c3 = st.columns(3)
    if c1.button("修正を依頼", key=f"{key_prefix}_request", use_container_width=True):
        return "request_changes"
    if c2.button("承認", key=f"{key_prefix}_approve", use_container_width=True, type="primary"):
        return "approve"
    c3.button(
        "公開準備",
        key=f"{key_prefix}_prepare",
        use_container_width=True,
        disabled=True,
        help="Production操作は禁止されています。承認後も手動レビューが必要です。",
    )
    return None


def evidence_status_legend() -> None:
    """Render the evidence-state vocabulary without inferring any record state."""
    st.markdown(
        '<div class="aios-state-legend" aria-label="Evidence status legend">'
        '<span class="aios-state-label state-proposal" aria-label="PROPOSAL: proposal only">PROPOSAL</span>'
        '<span class="aios-state-label state-verified" aria-label="VERIFIED: evidence confirmed">VERIFIED</span>'
        '<span class="aios-state-label state-blocked" aria-label="BLOCKED: blocking reason recorded">BLOCKED</span>'
        '<span class="aios-state-label state-na" aria-label="N/A: not applicable or no verified value">N/A</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def glass_card(title: str, body: str, *, metric: str | None = None) -> None:
    """Render a presentation-only card without coupling UI code to engine state."""
    metric_html = f'<div class="aios-number">{html.escape(metric)}</div>' if metric is not None else ""
    st.markdown(
        f'<section class="aios-card"><h4>{html.escape(title)}</h4>{metric_html}'
        f'<div class="aios-muted">{html.escape(body)}</div></section>',
        unsafe_allow_html=True,
    )


def status_badge(label: str, *, state: str = "idle") -> str:
    """Return escaped badge markup for status rows and workflow steps."""
    allowed = {"ok", "run", "warn", "stop", "idle"}
    safe_state = state if state in allowed else "idle"
    return f'<span class="aios-badge aios-{safe_state}">{html.escape(label)}</span>'


def approval_panel(message: str, *, state: str = "review") -> None:
    css_class = "aios-error" if state == "error" else "aios-warning" if state == "warning" else "aios-approval"
    st.markdown(
        f'<section class="{css_class}" role="status"><strong>Approval</strong><br>{html.escape(message)}</section>',
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(f'<section class="aios-empty" role="status">{html.escape(message)}</section>', unsafe_allow_html=True)


def loading_state(message: str) -> None:
    st.markdown(f'<section class="aios-loading" role="status">{html.escape(message)}</section>', unsafe_allow_html=True)


def error_state(message: str) -> None:
    st.markdown(f'<section class="aios-error" role="alert">{html.escape(message)}</section>', unsafe_allow_html=True)
