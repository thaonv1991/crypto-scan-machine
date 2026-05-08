"""
Scan Processor - Orchestrates data collection from all engines.
Handles discovering new projects, collecting market/social/on-chain data,
and storing results in the database.
"""

from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import RedFlag
from app.models.onchain import OnchainData
from app.models.project import Project, ProjectStatus
from app.models.timeseries import MarketData, SocialData
from app.services.collectors.coingecko import CoinGeckoCollector
from app.services.collectors.dexscreener import DexScreenerCollector
from app.services.collectors.goplus import BLOCKCHAIN_TO_CHAIN_ID, GoPlusCollector
from app.services.collectors.reddit import RedditCollector

logger = structlog.get_logger()


class ScanProcessor:
    """Orchestrates scanning and data collection across all engines."""

    def __init__(self):
        self.dexscreener = DexScreenerCollector()
        self.coingecko = CoinGeckoCollector()
        self.goplus = GoPlusCollector()
        self.reddit = RedditCollector()

    async def close_all(self) -> None:
        await self.dexscreener.close()
        await self.coingecko.close()
        await self.goplus.close()
        await self.reddit.close()

    # --- Engine 1: New Project Discovery ---

    async def scan_new_projects_dexscreener(self, db: AsyncSession) -> int:
        """Discover new projects from DexScreener latest listings."""
        created_count = 0
        try:
            profiles = await self.dexscreener.get_latest_token_profiles()
            logger.info("scan.dexscreener_profiles", count=len(profiles))

            for raw in profiles:
                normalized = self.dexscreener.normalize_token_profile(raw)
                slug = normalized["slug"]

                existing = await db.execute(select(Project).where(Project.slug == slug))
                if existing.scalar_one_or_none():
                    continue

                project = Project(
                    name=normalized["name"],
                    symbol=normalized.get("symbol"),
                    slug=slug,
                    contract_address=normalized.get("contract_address"),
                    blockchain=normalized.get("blockchain", "ethereum"),
                    website=normalized.get("website"),
                    description=normalized.get("description"),
                    logo_url=normalized.get("logo_url"),
                    twitter_url=normalized.get("twitter_url"),
                    telegram_url=normalized.get("telegram_url"),
                    discord_url=normalized.get("discord_url"),
                    source="dexscreener",
                    status=ProjectStatus.NEW.value,
                    extra_data=normalized.get("extra_data", {}),
                )
                db.add(project)
                created_count += 1

            if created_count > 0:
                await db.flush()
                logger.info("scan.new_projects_created", source="dexscreener", count=created_count)

        except Exception as e:
            logger.error("scan.dexscreener_failed", error=str(e))

        return created_count

    async def scan_trending_coingecko(self, db: AsyncSession) -> int:
        """Discover trending projects from CoinGecko."""
        created_count = 0
        try:
            trending = await self.coingecko.get_trending_coins()
            logger.info("scan.coingecko_trending", count=len(trending))

            for coin in trending:
                coin_id = coin.get("id", "")
                slug = f"coingecko-{coin_id}"

                existing = await db.execute(select(Project).where(Project.slug == slug))
                if existing.scalar_one_or_none():
                    continue

                normalized = self.coingecko.normalize_to_project(coin)
                project = Project(
                    name=normalized["name"],
                    symbol=normalized.get("symbol"),
                    slug=slug,
                    contract_address=normalized.get("contract_address"),
                    blockchain=normalized.get("blockchain", "ethereum"),
                    website=normalized.get("website"),
                    description=normalized.get("description"),
                    logo_url=normalized.get("logo_url"),
                    source="coingecko",
                    status=ProjectStatus.NEW.value,
                    extra_data=normalized.get("extra_data", {}),
                )
                db.add(project)
                created_count += 1

            if created_count > 0:
                await db.flush()
                logger.info("scan.new_projects_created", source="coingecko", count=created_count)

        except Exception as e:
            logger.error("scan.coingecko_trending_failed", error=str(e))

        return created_count

    # --- Engine 2: Market Data Collection ---

    async def collect_market_data_dexscreener(self, db: AsyncSession) -> int:
        """Collect market data from DexScreener for projects with contract addresses."""
        collected = 0
        try:
            result = await db.execute(
                select(Project).where(
                    Project.is_active.is_(True),
                    Project.contract_address.isnot(None),
                    Project.contract_address != "",
                )
            )
            projects = result.scalars().all()
            logger.info("market.dexscreener_collecting", project_count=len(projects))

            for project in projects:
                try:
                    pairs = await self.dexscreener.get_token_info(project.contract_address)
                    if not pairs:
                        continue

                    top_pair = pairs[0]
                    market = self.dexscreener.normalize_pair_to_market_data(top_pair)

                    market_data = MarketData(
                        time=datetime.now(timezone.utc),
                        project_id=project.id,
                        price_usd=market.get("price_usd"),
                        volume_24h=market.get("volume_24h"),
                        market_cap=market.get("market_cap"),
                        fdv=market.get("fdv"),
                        liquidity_usd=market.get("liquidity_usd"),
                        price_change_1h=market.get("price_change_1h"),
                        price_change_24h=market.get("price_change_24h"),
                        buy_count=market.get("buy_count"),
                        sell_count=market.get("sell_count"),
                        source="dexscreener",
                        extra_data=market.get("extra_data"),
                    )
                    db.add(market_data)
                    collected += 1
                except Exception as e:
                    logger.error(
                        "market.dexscreener_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

            if collected > 0:
                await db.flush()
                logger.info("market.dexscreener_collected", count=collected)

        except Exception as e:
            logger.error("market.dexscreener_failed", error=str(e))

        return collected

    async def collect_market_data_coingecko(self, db: AsyncSession) -> int:
        """Collect market data from CoinGecko for top coins."""
        collected = 0
        try:
            coins = await self.coingecko.get_coins_markets(per_page=100, page=1)
            logger.info("market.coingecko_fetched", count=len(coins))

            for coin in coins:
                coin_id = coin.get("id", "")
                slug = f"coingecko-{coin_id}"

                result = await db.execute(select(Project).where(Project.slug == slug))
                project = result.scalar_one_or_none()

                if not project:
                    normalized = self.coingecko.normalize_to_project(coin)
                    project = Project(
                        name=normalized["name"],
                        symbol=normalized.get("symbol"),
                        slug=slug,
                        blockchain="ethereum",
                        source="coingecko",
                        status=ProjectStatus.MONITORING.value,
                        logo_url=normalized.get("logo_url"),
                        extra_data=normalized.get("extra_data", {}),
                    )
                    db.add(project)
                    await db.flush()

                market = self.coingecko.normalize_market_data(coin)
                market_data = MarketData(
                    time=datetime.now(timezone.utc),
                    project_id=project.id,
                    price_usd=market.get("price_usd"),
                    volume_24h=market.get("volume_24h"),
                    market_cap=market.get("market_cap"),
                    fdv=market.get("fdv"),
                    price_change_1h=market.get("price_change_1h"),
                    price_change_24h=market.get("price_change_24h"),
                    price_change_7d=market.get("price_change_7d"),
                    source="coingecko",
                    extra_data=market.get("extra_data"),
                )
                db.add(market_data)
                collected += 1

            if collected > 0:
                await db.flush()
                logger.info("market.coingecko_collected", count=collected)

        except Exception as e:
            logger.error("market.coingecko_failed", error=str(e))

        return collected

    # --- Engine 3: Social Data Collection ---

    async def collect_social_data_reddit(self, db: AsyncSession) -> int:
        """Collect social data from Reddit for projects with subreddit info."""
        collected = 0
        try:
            result = await db.execute(
                select(Project).where(
                    Project.is_active.is_(True),
                    Project.extra_data.isnot(None),
                )
            )
            projects = result.scalars().all()

            for project in projects:
                extra = project.extra_data or {}
                subreddit_url = extra.get("subreddit_url", "")
                if not subreddit_url:
                    continue

                subreddit_name = subreddit_url.rstrip("/").split("/")[-1]
                if not subreddit_name or subreddit_name == "null":
                    continue

                try:
                    about = await self.reddit.get_subreddit_about(subreddit_name)
                    if not about:
                        continue

                    normalized = self.reddit.normalize_to_social_data(about)
                    social_data = SocialData(
                        time=datetime.now(timezone.utc),
                        project_id=project.id,
                        reddit_subscribers=normalized.get("reddit_subscribers"),
                        reddit_active_users=normalized.get("reddit_active_users"),
                        source="reddit",
                        extra_data=normalized.get("extra_data"),
                    )
                    db.add(social_data)
                    collected += 1
                except Exception as e:
                    logger.error(
                        "social.reddit_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

            if collected > 0:
                await db.flush()
                logger.info("social.reddit_collected", count=collected)

        except Exception as e:
            logger.error("social.reddit_failed", error=str(e))

        return collected

    # --- Engine 4: On-chain Security Analysis ---

    async def collect_onchain_goplus(self, db: AsyncSession) -> int:
        """Collect on-chain security data from GoPlus for projects with contract addresses."""
        collected = 0
        try:
            result = await db.execute(
                select(Project).where(
                    Project.is_active.is_(True),
                    Project.contract_address.isnot(None),
                    Project.contract_address != "",
                )
            )
            projects = result.scalars().all()
            logger.info("onchain.goplus_collecting", project_count=len(projects))

            for project in projects:
                chain_id = BLOCKCHAIN_TO_CHAIN_ID.get(project.blockchain)
                if not chain_id:
                    continue

                try:
                    security = await self.goplus.get_token_security(chain_id, project.contract_address)
                    if not security:
                        continue

                    normalized = self.goplus.normalize_to_onchain_data(security, project.blockchain)
                    onchain = OnchainData(
                        project_id=project.id,
                        holder_count=normalized.get("holder_count"),
                        total_supply=normalized.get("total_supply"),
                        top10_holder_pct=normalized.get("top10_holder_pct"),
                        is_verified=normalized.get("is_verified"),
                        is_renounced=normalized.get("is_renounced"),
                        has_proxy=normalized.get("has_proxy"),
                        has_mint_function=normalized.get("has_mint_function"),
                        has_blacklist=normalized.get("has_blacklist"),
                        buy_tax=normalized.get("buy_tax"),
                        sell_tax=normalized.get("sell_tax"),
                        blockchain=project.blockchain,
                        source="goplus",
                        extra_data=normalized.get("extra_data"),
                    )
                    db.add(onchain)

                    flags = self.goplus.detect_red_flags(security, project.contract_address)
                    for flag_data in flags:
                        existing_flag = await db.execute(
                            select(RedFlag).where(
                                RedFlag.project_id == project.id,
                                RedFlag.flag_type == flag_data["flag_type"],
                                RedFlag.is_active.is_(True),
                            )
                        )
                        if existing_flag.scalar_one_or_none():
                            continue

                        red_flag = RedFlag(
                            project_id=project.id,
                            flag_type=flag_data["flag_type"],
                            severity=flag_data["severity"],
                            title=flag_data["title"],
                            description=flag_data.get("description"),
                            detected_by=flag_data["detected_by"],
                            engine=flag_data["engine"],
                            confidence=flag_data.get("confidence", 0.0),
                        )
                        db.add(red_flag)

                    collected += 1
                except Exception as e:
                    logger.error(
                        "onchain.goplus_project_failed",
                        project_id=str(project.id),
                        error=str(e),
                    )

            if collected > 0:
                await db.flush()
                logger.info("onchain.goplus_collected", count=collected)

        except Exception as e:
            logger.error("onchain.goplus_failed", error=str(e))

        return collected
