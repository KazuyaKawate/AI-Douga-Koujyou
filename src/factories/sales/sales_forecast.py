"""Sales forecast — rule-based pipeline calculation. No external API calls."""
from datetime import date
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sales_settings.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            import json
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"monthly_target": 100000, "default_probability_by_stage": {}}


def calculate_forecast(leads_data: dict, deals_data: dict) -> dict:
    deals = deals_data.get("deals", [])
    leads = leads_data.get("leads", [])
    settings = load_settings()
    monthly_target = settings.get("monthly_target", 100000)

    active_deals = [d for d in deals if d.get("status") == "active"]
    contracted_deals = [d for d in deals if d.get("status") == "won"]
    lost_deals = [d for d in deals if d.get("status") == "lost"]

    pipeline_total = sum(d.get("amount", 0) for d in active_deals)
    weighted_forecast = sum(
        d.get("amount", 0) * d.get("probability", 0) / 100
        for d in active_deals
    )
    contracted_total = sum(d.get("amount", 0) for d in contracted_deals)

    total_closed = len(contracted_deals) + len(lost_deals)
    conversion_rate = (len(contracted_deals) / total_closed * 100) if total_closed > 0 else 0.0

    expected_monthly = contracted_total + weighted_forecast

    total_leads = len(leads)
    contracted_leads = sum(1 for l in leads if l.get("status") == "contracted")
    lead_conversion_rate = (contracted_leads / total_leads * 100) if total_leads > 0 else 0.0

    target_attainment = (expected_monthly / monthly_target * 100) if monthly_target > 0 else 0.0

    return {
        "pipeline_total":     int(pipeline_total),
        "weighted_forecast":  int(weighted_forecast),
        "contracted_total":   int(contracted_total),
        "expected_monthly":   int(expected_monthly),
        "monthly_target":     monthly_target,
        "target_attainment":  round(target_attainment, 1),
        "conversion_rate":    round(conversion_rate, 1),
        "lead_conversion_rate": round(lead_conversion_rate, 1),
        "active_deal_count":  len(active_deals),
        "contracted_count":   len(contracted_deals),
        "lost_count":         len(lost_deals),
        "total_lead_count":   total_leads,
    }


def get_pipeline_by_stage(deals_data: dict) -> dict:
    from src.factories.sales.deal_manager import STAGES, STAGE_LABELS, STAGE_ICONS
    deals = deals_data.get("deals", [])
    result = {}
    for stage in STAGES:
        stage_deals = [d for d in deals if d.get("stage") == stage and d.get("status") == "active"]
        result[stage] = {
            "label":  STAGE_LABELS.get(stage, stage),
            "icon":   STAGE_ICONS.get(stage, ""),
            "count":  len(stage_deals),
            "amount": sum(d.get("amount", 0) for d in stage_deals),
            "deals":  stage_deals,
        }
    return result


def get_monthly_projection(deals_data: dict) -> dict:
    today = date.today()
    year_month = f"{today.year}-{today.month:02d}"
    deals = deals_data.get("deals", [])

    expected_close_this_month = [
        d for d in deals
        if d.get("status") == "active"
        and d.get("expected_close_date", "")[:7] == year_month
    ]
    projected_revenue = sum(
        d.get("amount", 0) * d.get("probability", 0) / 100
        for d in expected_close_this_month
    )
    contracted_this_month = [
        d for d in deals
        if d.get("status") == "won"
        and (d.get("contracted_at") or "")[:7] == year_month
    ]
    contracted_revenue = sum(d.get("amount", 0) for d in contracted_this_month)

    return {
        "year_month":         year_month,
        "closing_this_month": len(expected_close_this_month),
        "projected_revenue":  int(projected_revenue),
        "contracted_revenue": int(contracted_revenue),
        "total_forecast":     int(projected_revenue + contracted_revenue),
    }
