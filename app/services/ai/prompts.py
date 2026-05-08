"""Prompt engineering for AI-powered crypto analysis.

Contains system prompts and data formatting functions for comprehensive
token/project analysis using LLMs.
"""

SYSTEM_PROMPT = """You are an expert cryptocurrency analyst and blockchain security researcher.
Your job is to analyze crypto tokens/projects and provide actionable intelligence.

You MUST respond in valid JSON format with the following structure:
{
    "overall_score": <float 0-100>,
    "confidence": <float 0-1>,
    "recommendation": "<STRONG_BUY|BUY|HOLD|AVOID|STRONG_AVOID>",
    "summary": "<2-3 sentence executive summary>",
    "risk_level": "<very_low|low|medium|high|very_high>",
    "analysis": {
        "tokenomics": {
            "score": <float 0-100>,
            "findings": ["<finding1>", "<finding2>"]
        },
        "market_health": {
            "score": <float 0-100>,
            "findings": ["<finding1>", "<finding2>"]
        },
        "security": {
            "score": <float 0-100>,
            "findings": ["<finding1>", "<finding2>"]
        },
        "community": {
            "score": <float 0-100>,
            "findings": ["<finding1>", "<finding2>"]
        },
        "potential": {
            "score": <float 0-100>,
            "findings": ["<finding1>", "<finding2>"]
        }
    },
    "red_flags": [
        {
            "type": "<flag_type>",
            "severity": "<critical|high|medium|low>",
            "description": "<description>"
        }
    ],
    "catalysts": ["<positive catalyst 1>", "<positive catalyst 2>"],
    "risks": ["<risk 1>", "<risk 2>"],
    "verdict": "<detailed 3-5 sentence analysis conclusion>"
}

Analysis criteria:
1. TOKENOMICS: Supply distribution, inflation/deflation, vesting schedules, burn mechanisms
2. MARKET HEALTH: Liquidity depth, volume authenticity, price stability, market cap tier
3. SECURITY: Contract verification, ownership renouncement, honeypot risk, tax levels, audit status
4. COMMUNITY: Social media presence, engagement quality, community growth trajectory
5. POTENTIAL: Use case viability, competitive positioning, growth catalysts, market timing

Be brutally honest. Flag ALL suspicious patterns. Do not sugarcoat risks.
If data is insufficient, say so and lower your confidence score accordingly."""


def build_analysis_prompt(project_data: dict) -> str:
    """Build a comprehensive analysis prompt from all available project data."""
    sections = []

    sections.append("# Project Analysis Request\n")

    name = project_data.get("name", "Unknown")
    symbol = project_data.get("symbol", "")
    blockchain = project_data.get("blockchain", "unknown")
    contract = project_data.get("contract_address", "N/A")

    sections.append(f"**Token:** {name} ({symbol})")
    sections.append(f"**Blockchain:** {blockchain}")
    sections.append(f"**Contract:** {contract}")
    sections.append(f"**Source:** {project_data.get('source', 'unknown')}")
    sections.append(f"**Status:** {project_data.get('status', 'unknown')}")

    if project_data.get("description"):
        sections.append(f"**Description:** {project_data['description']}")
    if project_data.get("category"):
        sections.append(f"**Category:** {project_data['category']}")
    if project_data.get("website"):
        sections.append(f"**Website:** {project_data['website']}")

    market = project_data.get("market_data", {})
    if market:
        sections.append("\n## Market Data (Latest)")
        if market.get("price_usd") is not None:
            sections.append(f"- Price: ${market['price_usd']:,.8f}")
        if market.get("market_cap") is not None:
            sections.append(f"- Market Cap: ${market['market_cap']:,.0f}")
        if market.get("fdv") is not None:
            sections.append(f"- FDV: ${market['fdv']:,.0f}")
        if market.get("volume_24h") is not None:
            sections.append(f"- 24h Volume: ${market['volume_24h']:,.0f}")
        if market.get("liquidity_usd") is not None:
            sections.append(f"- Liquidity: ${market['liquidity_usd']:,.0f}")
        if market.get("price_change_1h") is not None:
            sections.append(f"- 1h Change: {market['price_change_1h']:.2f}%")
        if market.get("price_change_24h") is not None:
            sections.append(f"- 24h Change: {market['price_change_24h']:.2f}%")
        if market.get("price_change_7d") is not None:
            sections.append(f"- 7d Change: {market['price_change_7d']:.2f}%")
        if market.get("buy_count") is not None and market.get("sell_count") is not None:
            total = market["buy_count"] + market["sell_count"]
            if total > 0:
                buy_pct = market["buy_count"] / total * 100
                sections.append(
                    f"- Buy/Sell: {market['buy_count']}/{market['sell_count']} ({buy_pct:.0f}% buy)"
                )
        if market.get("holders_count") is not None:
            sections.append(f"- Holders: {market['holders_count']:,}")

    scores = project_data.get("engine_scores", {})
    if scores:
        sections.append("\n## Current Engine Scores (0-100)")
        sections.append(f"- Engine 1 (Discovery): {scores.get('engine1', 0):.1f}")
        sections.append(f"- Engine 2 (Market): {scores.get('engine2', 0):.1f}")
        sections.append(f"- Engine 3 (Social): {scores.get('engine3', 0):.1f}")
        sections.append(f"- Engine 4 (Security): {scores.get('engine4', 0):.1f}")
        sections.append(f"- Total (weighted, excl. AI): {scores.get('total', 0):.1f}")

    onchain = project_data.get("onchain_data", {})
    if onchain:
        sections.append("\n## On-Chain Security Data")
        if onchain.get("is_verified") is not None:
            sections.append(f"- Contract Verified: {onchain['is_verified']}")
        if onchain.get("is_renounced") is not None:
            sections.append(f"- Ownership Renounced: {onchain['is_renounced']}")
        if onchain.get("has_proxy") is not None:
            sections.append(f"- Has Proxy: {onchain['has_proxy']}")
        if onchain.get("has_mint_function") is not None:
            sections.append(f"- Has Mint Function: {onchain['has_mint_function']}")
        if onchain.get("has_blacklist") is not None:
            sections.append(f"- Has Blacklist: {onchain['has_blacklist']}")
        if onchain.get("buy_tax") is not None:
            sections.append(f"- Buy Tax: {onchain['buy_tax']}%")
        if onchain.get("sell_tax") is not None:
            sections.append(f"- Sell Tax: {onchain['sell_tax']}%")
        if onchain.get("holder_count") is not None:
            sections.append(f"- Holder Count: {onchain['holder_count']:,}")
        if onchain.get("top10_holder_pct") is not None:
            sections.append(f"- Top 10 Holders: {onchain['top10_holder_pct']:.1f}%")
        if onchain.get("liquidity_locked") is not None:
            sections.append(f"- Liquidity Locked: {onchain['liquidity_locked']}")

    social = project_data.get("social_data", {})
    if social:
        sections.append("\n## Social Media Data")
        if social.get("twitter_followers") is not None:
            sections.append(f"- Twitter Followers: {social['twitter_followers']:,}")
        if social.get("twitter_engagement_rate") is not None:
            sections.append(f"- Twitter Engagement: {social['twitter_engagement_rate']:.2f}%")
        if social.get("telegram_members") is not None:
            sections.append(f"- Telegram Members: {social['telegram_members']:,}")
        if social.get("telegram_online") is not None:
            sections.append(f"- Telegram Online: {social['telegram_online']:,}")
        if social.get("reddit_subscribers") is not None:
            sections.append(f"- Reddit Subscribers: {social['reddit_subscribers']:,}")
        if social.get("reddit_active_users") is not None:
            sections.append(f"- Reddit Active: {social['reddit_active_users']:,}")
        if social.get("sentiment_label"):
            sections.append(f"- Sentiment: {social['sentiment_label']}")

    red_flags = project_data.get("red_flags", [])
    if red_flags:
        sections.append("\n## Detected Red Flags")
        for flag in red_flags:
            severity = flag.get("severity", "unknown")
            title = flag.get("title", "Unknown flag")
            sections.append(f"- [{severity.upper()}] {title}")

    social_links = []
    if project_data.get("twitter_url"):
        social_links.append(f"Twitter: {project_data['twitter_url']}")
    if project_data.get("telegram_url"):
        social_links.append(f"Telegram: {project_data['telegram_url']}")
    if project_data.get("discord_url"):
        social_links.append(f"Discord: {project_data['discord_url']}")
    if project_data.get("github_url"):
        social_links.append(f"GitHub: {project_data['github_url']}")
    if social_links:
        sections.append("\n## Social Links")
        for link in social_links:
            sections.append(f"- {link}")

    sections.append("\n---")
    sections.append("Analyze this project thoroughly. Be specific about risks and opportunities.")
    sections.append("Consider the blockchain ecosystem, current market conditions, and comparable projects.")
    sections.append("If critical data is missing, note it and adjust confidence accordingly.")

    return "\n".join(sections)


QUICK_SCAN_SYSTEM = """You are a rapid crypto token scanner. Analyze the token data and respond in JSON:
{
    "score": <float 0-100>,
    "risk": "<low|medium|high|critical>",
    "verdict": "<1 sentence>",
    "flags": ["<flag1>", "<flag2>"]
}
Be concise. Focus on immediate red flags and risk assessment."""


def build_quick_scan_prompt(project_data: dict) -> str:
    """Build a minimal prompt for quick scanning (lower token usage)."""
    parts = []
    name = project_data.get("name", "Unknown")
    symbol = project_data.get("symbol", "")
    parts.append(f"Token: {name} ({symbol}) on {project_data.get('blockchain', '?')}")

    market = project_data.get("market_data", {})
    if market:
        if market.get("price_usd"):
            parts.append(f"Price: ${market['price_usd']}")
        if market.get("market_cap"):
            parts.append(f"MCap: ${market['market_cap']:,.0f}")
        if market.get("liquidity_usd"):
            parts.append(f"Liq: ${market['liquidity_usd']:,.0f}")
        if market.get("volume_24h"):
            parts.append(f"Vol24h: ${market['volume_24h']:,.0f}")

    onchain = project_data.get("onchain_data", {})
    if onchain:
        flags = []
        if onchain.get("is_verified") is False:
            flags.append("UNVERIFIED")
        if onchain.get("has_mint_function") is True:
            flags.append("MINTABLE")
        if onchain.get("buy_tax") and onchain["buy_tax"] > 5:
            flags.append(f"BUY_TAX={onchain['buy_tax']}%")
        if onchain.get("sell_tax") and onchain["sell_tax"] > 5:
            flags.append(f"SELL_TAX={onchain['sell_tax']}%")
        if flags:
            parts.append(f"Flags: {', '.join(flags)}")

    return " | ".join(parts)


COMPARISON_SYSTEM = """You are a crypto comparative analyst. Compare the given projects and respond in JSON:
{
    "ranking": [{"name": "<name>", "score": <float>, "reason": "<1 sentence>"}],
    "best_pick": "<name>",
    "avoid": "<name or null>",
    "analysis": "<2-3 sentence comparison>"
}
Rank from best to worst investment opportunity."""


def build_comparison_prompt(projects: list[dict]) -> str:
    """Build a prompt to compare multiple projects."""
    parts = ["Compare these crypto projects:\n"]
    for i, p in enumerate(projects, 1):
        name = p.get("name", "Unknown")
        symbol = p.get("symbol", "")
        score = p.get("total_score", 0)
        market = p.get("market_data", {})
        mcap = market.get("market_cap", 0)
        vol = market.get("volume_24h", 0)
        liq = market.get("liquidity_usd", 0)
        parts.append(
            f"{i}. {name} ({symbol}) — Score: {score:.1f}, "
            f"MCap: ${mcap:,.0f}, Vol: ${vol:,.0f}, Liq: ${liq:,.0f}"
        )
    return "\n".join(parts)
