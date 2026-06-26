"""Revenue Tracker — per-article revenue management and monthly summaries."""
from datetime import date
from src.factories.note.article_manager import load_articles, save_articles


def update_revenue(article_id: str, price: int = None, sales_count: int = None,
                   actual_revenue: int = None, view_count: int = None,
                   like_count: int = None) -> dict:
    """Update revenue fields for a specific article."""
    data = load_articles()
    for article in data.get("articles", []):
        if article["id"] == article_id:
            if price is not None:
                article["price"] = price
                article["estimated_revenue"] = price * article.get("sales_count", 0)
            if sales_count is not None:
                article["sales_count"] = sales_count
                article["estimated_revenue"] = article.get("price", 0) * sales_count
            if actual_revenue is not None:
                article["actual_revenue"] = actual_revenue
            if view_count is not None:
                article["view_count"] = view_count
            if like_count is not None:
                article["like_count"] = like_count
            break
    save_articles(data)
    return data


def get_revenue_summary(data: dict) -> dict:
    """Aggregate revenue stats across all published articles."""
    articles = data.get("articles", [])
    published = [a for a in articles if a.get("status") == "published"]

    total_estimated = sum(a.get("estimated_revenue", 0) for a in published)
    total_actual = sum(a.get("actual_revenue", 0) for a in published)
    total_sales = sum(a.get("sales_count", 0) for a in published)
    total_views = sum(a.get("view_count", 0) for a in published)
    total_likes = sum(a.get("like_count", 0) for a in published)
    paid_articles = [a for a in published if a.get("price", 0) > 0]
    free_articles = [a for a in published if a.get("price", 0) == 0]

    avg_price = (
        sum(a.get("price", 0) for a in paid_articles) / len(paid_articles)
        if paid_articles else 0
    )

    top_earner = max(published, key=lambda a: a.get("actual_revenue", 0), default=None)

    today = date.today().isoformat()
    month_prefix = today[:7]
    this_month = [
        a for a in published
        if (a.get("published_at") or "")[:7] == month_prefix
    ]
    month_revenue = sum(a.get("actual_revenue", 0) for a in this_month)

    return {
        "total_articles": len(published),
        "paid_articles": len(paid_articles),
        "free_articles": len(free_articles),
        "total_estimated_revenue": total_estimated,
        "total_actual_revenue": total_actual,
        "total_sales": total_sales,
        "total_views": total_views,
        "total_likes": total_likes,
        "avg_price": avg_price,
        "top_earner": top_earner,
        "month_revenue": month_revenue,
        "revenue_gap": total_estimated - total_actual,
    }


def get_article_revenue_rows(data: dict) -> list[dict]:
    """Return per-article revenue rows for display table."""
    articles = data.get("articles", [])
    rows = []
    for a in articles:
        if a.get("status") not in ("published", "archived"):
            continue
        price = a.get("price", 0)
        sales = a.get("sales_count", 0)
        est = price * sales
        actual = a.get("actual_revenue", 0)
        rows.append({
            "id": a["id"],
            "title": a.get("title", ""),
            "status": a.get("status", ""),
            "published_at": a.get("published_at", ""),
            "price": price,
            "sales_count": sales,
            "estimated_revenue": est,
            "actual_revenue": actual,
            "view_count": a.get("view_count", 0),
            "like_count": a.get("like_count", 0),
            "note_url": a.get("note_url", ""),
        })
    rows.sort(key=lambda r: r["published_at"], reverse=True)
    return rows
