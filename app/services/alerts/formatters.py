"""Alert message formatters for Telegram.

Generates HTML-formatted messages for different alert types:
- New high-score project discovered
- Score spike (significant increase)
- Score drop (significant decrease)
- Critical red flag detected
- AI analysis complete
- Daily summary report
"""

from datetime import datetime, timezone


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram HTML mode."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _score_emoji(score: float) -> str:
    if score >= 80:
        return "🟢"
    if score >= 60:
        return "🔵"
    if score >= 40:
        return "🟡"
    if score >= 20:
        return "🟠"
    return "🔴"


def _risk_emoji(risk: str) -> str:
    return {
        "very_low": "✅",
        "low": "🟢",
        "medium": "🟡",
        "high": "🟠",
        "very_high": "🔴",
        "critical": "🚨",
    }.get(risk, "❓")


def _recommendation_emoji(rec: str) -> str:
    return {
        "STRONG_BUY": "🚀",
        "BUY": "💰",
        "HOLD": "⏸",
        "AVOID": "⚠️",
        "STRONG_AVOID": "🚫",
    }.get(rec, "❓")


def _format_number(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.2f}B"
        if value >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        if value >= 1_000:
            return f"${value / 1_000:,.1f}K"
        return f"${value:,.2f}"
    return f"{value:,}"


def format_new_project_alert(project_data: dict) -> str:
    """Format alert for a newly discovered high-score project."""
    name = _escape_html(project_data.get("name", "Unknown"))
    symbol = _escape_html(project_data.get("symbol", "???"))
    blockchain = _escape_html(project_data.get("blockchain", "unknown"))
    score = project_data.get("total_score", 0)
    emoji = _score_emoji(score)

    lines = [
        "🆕 <b>New Project Detected</b>",
        "",
        f"{emoji} <b>{name}</b> ({symbol})",
        f"📊 Score: <b>{score:.1f}/100</b>",
        f"⛓ Chain: {blockchain}",
    ]

    market = project_data.get("market_data", {})
    if market:
        if market.get("price_usd") is not None:
            lines.append(f"💲 Price: ${market['price_usd']:,.8f}")
        if market.get("market_cap") is not None:
            lines.append(f"📈 MCap: {_format_number(market['market_cap'])}")
        if market.get("liquidity_usd") is not None:
            lines.append(f"💧 Liquidity: {_format_number(market['liquidity_usd'])}")
        if market.get("volume_24h") is not None:
            lines.append(f"📊 Vol 24h: {_format_number(market['volume_24h'])}")

    scores = project_data.get("engine_scores", {})
    if scores:
        lines.append("")
        lines.append("<b>Engine Scores:</b>")
        lines.append(
            f"  Discovery: {scores.get('engine1', 0):.0f} | "
            f"Market: {scores.get('engine2', 0):.0f} | "
            f"Social: {scores.get('engine3', 0):.0f}"
        )
        lines.append(
            f"  Security: {scores.get('engine4', 0):.0f} | "
            f"AI: {scores.get('engine5', 0):.0f}"
        )

    contract = project_data.get("contract_address")
    if contract:
        lines.append(f"\n🔗 <code>{_escape_html(contract)}</code>")

    source = project_data.get("source", "")
    if source:
        lines.append(f"📡 Source: {_escape_html(source)}")

    lines.append(f"\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


def format_score_change_alert(project_data: dict, old_score: float, new_score: float) -> str:
    """Format alert for significant score change."""
    name = _escape_html(project_data.get("name", "Unknown"))
    symbol = _escape_html(project_data.get("symbol", "???"))
    delta = new_score - old_score
    emoji = _score_emoji(new_score)

    if delta > 0:
        direction = "📈 <b>Score Spike</b>"
        delta_str = f"+{delta:.1f}"
    else:
        direction = "📉 <b>Score Drop</b>"
        delta_str = f"{delta:.1f}"

    lines = [
        direction,
        "",
        f"{emoji} <b>{name}</b> ({symbol})",
        f"📊 Score: {old_score:.1f} → <b>{new_score:.1f}</b> ({delta_str})",
    ]

    market = project_data.get("market_data", {})
    if market.get("price_change_24h") is not None:
        lines.append(f"💲 24h Price: {market['price_change_24h']:+.2f}%")
    if market.get("volume_24h") is not None:
        lines.append(f"📊 Volume: {_format_number(market['volume_24h'])}")

    flags = project_data.get("red_flag_count", 0)
    if flags > 0:
        lines.append(f"🚩 Red Flags: {flags}")

    lines.append(f"\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


def format_red_flag_alert(project_data: dict, flag_data: dict) -> str:
    """Format alert for a critical red flag detection."""
    name = _escape_html(project_data.get("name", "Unknown"))
    symbol = _escape_html(project_data.get("symbol", "???"))
    severity = flag_data.get("severity", "medium")
    flag_type = _escape_html(flag_data.get("flag_type", "unknown"))
    description = _escape_html(flag_data.get("description", ""))
    detected_by = _escape_html(flag_data.get("detected_by", "system"))

    lines = [
        "🚨 <b>Critical Red Flag Detected</b>",
        "",
        f"🔴 <b>{name}</b> ({symbol})",
        f"⚠️ Type: <b>{flag_type}</b>",
        f"🔥 Severity: <b>{severity.upper()}</b>",
    ]

    if description:
        lines.append(f"📝 {description}")

    lines.append(f"🔍 Detected by: {detected_by}")

    score = project_data.get("total_score")
    if score is not None:
        lines.append(f"📊 Current Score: {score:.1f}")

    lines.append(f"\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


def format_ai_analysis_alert(project_data: dict, ai_result: dict) -> str:
    """Format alert for completed AI analysis."""
    name = _escape_html(project_data.get("name", "Unknown"))
    symbol = _escape_html(project_data.get("symbol", "???"))
    ai_score = ai_result.get("overall_score", 0)
    confidence = ai_result.get("confidence", 0)
    recommendation = ai_result.get("recommendation", "HOLD")
    risk_level = ai_result.get("risk_level", "medium")
    summary = ai_result.get("summary", "")
    rec_emoji = _recommendation_emoji(recommendation)
    risk_emoji = _risk_emoji(risk_level)

    lines = [
        "🤖 <b>AI Analysis Complete</b>",
        "",
        f"{_score_emoji(ai_score)} <b>{name}</b> ({symbol})",
        f"📊 AI Score: <b>{ai_score:.1f}/100</b> (Confidence: {confidence:.0%})",
        f"{rec_emoji} Recommendation: <b>{recommendation}</b>",
        f"{risk_emoji} Risk Level: <b>{risk_level}</b>",
    ]

    analysis = ai_result.get("analysis", {})
    if analysis:
        lines.append("")
        lines.append("<b>Sub-scores:</b>")
        for category in ("tokenomics", "market_health", "security", "community", "potential"):
            cat_data = analysis.get(category, {})
            if isinstance(cat_data, dict) and "score" in cat_data:
                cat_name = category.replace("_", " ").title()
                lines.append(f"  {_score_emoji(cat_data['score'])} {cat_name}: {cat_data['score']:.0f}")

    if summary:
        lines.append(f"\n💡 {_escape_html(summary[:500])}")

    red_flags = ai_result.get("red_flags", [])
    if red_flags:
        lines.append(f"\n🚩 <b>Red Flags ({len(red_flags)}):</b>")
        for flag in red_flags[:5]:
            sev = flag.get("severity", "?")
            desc = _escape_html(flag.get("description", ""))[:100]
            lines.append(f"  • [{sev.upper()}] {desc}")

    provider = ai_result.get("provider", "unknown")
    model = _escape_html(ai_result.get("model", "unknown"))
    lines.append(f"\n🔬 Model: {model} ({provider})")
    lines.append(f"🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)


def format_daily_summary(summary_data: dict) -> str:
    """Format a daily summary report."""
    total_projects = summary_data.get("total_projects", 0)
    new_projects = summary_data.get("new_projects", 0)
    avg_score = summary_data.get("avg_score", 0)
    alerts_sent = summary_data.get("alerts_sent", 0)
    ai_analyses = summary_data.get("ai_analyses", 0)

    lines = [
        "📋 <b>Daily Summary Report</b>",
        f"📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        f"📊 Total Projects: <b>{total_projects}</b>",
        f"🆕 New Today: <b>{new_projects}</b>",
        f"📈 Avg Score: <b>{avg_score:.1f}</b>",
        f"🔔 Alerts Sent: <b>{alerts_sent}</b>",
        f"🤖 AI Analyses: <b>{ai_analyses}</b>",
    ]

    top_projects = summary_data.get("top_projects", [])
    if top_projects:
        lines.append("")
        lines.append("<b>🏆 Top 10 Projects:</b>")
        for i, p in enumerate(top_projects[:10], 1):
            name = _escape_html(p.get("name", "?"))
            symbol = _escape_html(p.get("symbol", "?"))
            score = p.get("total_score", 0)
            emoji = _score_emoji(score)
            lines.append(f"  {i}. {emoji} {name} ({symbol}) — {score:.1f}")

    worst_flags = summary_data.get("critical_flags", [])
    if worst_flags:
        lines.append("")
        lines.append("<b>🚨 Critical Flags Today:</b>")
        for flag in worst_flags[:5]:
            name = _escape_html(flag.get("project_name", "?"))
            flag_type = _escape_html(flag.get("flag_type", "?"))
            lines.append(f"  • {name}: {flag_type}")

    lines.append(f"\n🕐 {datetime.now(timezone.utc).strftime('%H:%M UTC')}")
    return "\n".join(lines)


def format_watchlist_alert(project_data: dict, trigger_reason: str) -> str:
    """Format alert for a user watchlist trigger."""
    name = _escape_html(project_data.get("name", "Unknown"))
    symbol = _escape_html(project_data.get("symbol", "???"))
    score = project_data.get("total_score", 0)

    lines = [
        "⭐ <b>Watchlist Alert</b>",
        "",
        f"{_score_emoji(score)} <b>{name}</b> ({symbol})",
        f"📊 Score: <b>{score:.1f}/100</b>",
        f"📝 Trigger: {_escape_html(trigger_reason)}",
    ]

    market = project_data.get("market_data", {})
    if market.get("price_usd") is not None:
        lines.append(f"💲 Price: ${market['price_usd']:,.8f}")
    if market.get("price_change_24h") is not None:
        lines.append(f"📈 24h: {market['price_change_24h']:+.2f}%")

    lines.append(f"\n🕐 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    return "\n".join(lines)
