"""Initial schema with all tables and TimescaleDB hypertables

Revision ID: 001
Revises:
Create Date: 2026-05-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Core Tables ===

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("symbol", sa.String(50)),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("contract_address", sa.String(255)),
        sa.Column("blockchain", sa.String(50), server_default="ethereum"),
        sa.Column("pair_address", sa.String(255)),
        sa.Column("website", sa.String(500)),
        sa.Column("description", sa.Text),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("category", sa.String(100)),
        sa.Column("twitter_url", sa.String(500)),
        sa.Column("telegram_url", sa.String(500)),
        sa.Column("discord_url", sa.String(500)),
        sa.Column("github_url", sa.String(500)),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("launch_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("extra_data", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_blockchain", "projects", ["blockchain"])
    op.create_index("ix_projects_source", "projects", ["source"])
    op.create_index("ix_projects_discovered_at", "projects", ["discovered_at"])
    op.create_index("ix_projects_is_active", "projects", ["is_active"])
    op.create_index("ix_projects_contract_address", "projects", ["contract_address"])
    op.execute("CREATE INDEX ix_projects_name_trgm ON projects USING gin (name gin_trgm_ops)")

    op.create_table(
        "project_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine1_score", sa.Float, server_default="0"),
        sa.Column("engine2_score", sa.Float, server_default="0"),
        sa.Column("engine3_score", sa.Float, server_default="0"),
        sa.Column("engine4_score", sa.Float, server_default="0"),
        sa.Column("engine5_score", sa.Float, server_default="0"),
        sa.Column("total_score", sa.Float, server_default="0"),
        sa.Column("weights", postgresql.JSONB, server_default="{}"),
        sa.Column("score_breakdown", postgresql.JSONB, server_default="{}"),
        sa.Column("red_flag_count", sa.Integer, server_default="0"),
        sa.Column("has_critical_flag", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_project_scores_total", "project_scores", ["total_score"])
    op.create_index("ix_project_scores_project_created", "project_scores", ["project_id", "created_at"])

    op.create_table(
        "token_launches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True)),
        sa.Column("launchpad", sa.String(100), nullable=False),
        sa.Column("token_name", sa.String(255), nullable=False),
        sa.Column("token_symbol", sa.String(50)),
        sa.Column("blockchain", sa.String(50), nullable=False),
        sa.Column("raise_amount", sa.Float),
        sa.Column("token_price", sa.Float),
        sa.Column("fdv", sa.Float),
        sa.Column("initial_market_cap", sa.Float),
        sa.Column("sale_start", sa.DateTime(timezone=True)),
        sa.Column("sale_end", sa.DateTime(timezone=True)),
        sa.Column("tge_date", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(50), server_default="upcoming"),
        sa.Column("source_url", sa.String(500)),
        sa.Column("extra_data", postgresql.JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_token_launches_launchpad", "token_launches", ["launchpad"])
    op.create_index("ix_token_launches_blockchain", "token_launches", ["blockchain"])
    op.create_index("ix_token_launches_tge_date", "token_launches", ["tge_date"])
    op.create_index("ix_token_launches_status", "token_launches", ["status"])

    # === Time-Series Tables (will be hypertables) ===

    op.create_table(
        "market_data",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_usd", sa.Float),
        sa.Column("price_btc", sa.Float),
        sa.Column("price_eth", sa.Float),
        sa.Column("volume_24h", sa.Float),
        sa.Column("volume_change_pct", sa.Float),
        sa.Column("market_cap", sa.Float),
        sa.Column("fdv", sa.Float),
        sa.Column("liquidity_usd", sa.Float),
        sa.Column("liquidity_score", sa.Float),
        sa.Column("price_change_1h", sa.Float),
        sa.Column("price_change_24h", sa.Float),
        sa.Column("price_change_7d", sa.Float),
        sa.Column("buy_count", sa.Integer),
        sa.Column("sell_count", sa.Integer),
        sa.Column("holders_count", sa.Integer),
        sa.Column("source", sa.String(50), server_default="coingecko"),
        sa.Column("extra_data", postgresql.JSONB),
        sa.PrimaryKeyConstraint("time", "project_id"),
    )

    op.create_table(
        "social_data",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("twitter_followers", sa.Integer),
        sa.Column("twitter_following", sa.Integer),
        sa.Column("twitter_tweets_count", sa.Integer),
        sa.Column("twitter_engagement_rate", sa.Float),
        sa.Column("twitter_mentions_count", sa.Integer),
        sa.Column("telegram_members", sa.Integer),
        sa.Column("telegram_online", sa.Integer),
        sa.Column("telegram_messages_24h", sa.Integer),
        sa.Column("reddit_subscribers", sa.Integer),
        sa.Column("reddit_active_users", sa.Integer),
        sa.Column("reddit_posts_24h", sa.Integer),
        sa.Column("sentiment_score", sa.Float),
        sa.Column("sentiment_label", sa.String(20)),
        sa.Column("source", sa.String(50), server_default="twitter"),
        sa.Column("extra_data", postgresql.JSONB),
        sa.PrimaryKeyConstraint("time", "project_id"),
    )

    op.create_table(
        "score_history",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine1_score", sa.Float, server_default="0"),
        sa.Column("engine2_score", sa.Float, server_default="0"),
        sa.Column("engine3_score", sa.Float, server_default="0"),
        sa.Column("engine4_score", sa.Float, server_default="0"),
        sa.Column("engine5_score", sa.Float, server_default="0"),
        sa.Column("total_score", sa.Float, server_default="0"),
        sa.Column("score_delta", sa.Float),
        sa.Column("red_flag_count", sa.Integer, server_default="0"),
        sa.PrimaryKeyConstraint("time", "project_id"),
    )

    # Convert to TimescaleDB hypertables
    op.execute("SELECT create_hypertable('market_data', 'time', migrate_data => true)")
    op.execute("SELECT create_hypertable('social_data', 'time', migrate_data => true)")
    op.execute("SELECT create_hypertable('score_history', 'time', migrate_data => true)")

    # Add compression policies (compress after 7 days)
    op.execute("""
        ALTER TABLE market_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'project_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('market_data', INTERVAL '7 days')")

    op.execute("""
        ALTER TABLE social_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'project_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('social_data', INTERVAL '7 days')")

    op.execute("""
        ALTER TABLE score_history SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'project_id',
            timescaledb.compress_orderby = 'time DESC'
        )
    """)
    op.execute("SELECT add_compression_policy('score_history', INTERVAL '7 days')")

    # Add retention policies (drop raw data after 90 days for market/social)
    op.execute("SELECT add_retention_policy('market_data', INTERVAL '90 days')")
    op.execute("SELECT add_retention_policy('social_data', INTERVAL '90 days')")

    # Indexes on hypertables
    op.create_index("ix_market_data_project_time", "market_data", ["project_id", "time"])
    op.create_index("ix_social_data_project_time", "social_data", ["project_id", "time"])
    op.create_index("ix_score_history_project_time", "score_history", ["project_id", "time"])
    op.create_index("ix_score_history_total", "score_history", ["total_score"])

    # === Supporting Tables ===

    op.create_table(
        "onchain_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_supply", sa.Float),
        sa.Column("circulating_supply", sa.Float),
        sa.Column("burn_amount", sa.Float),
        sa.Column("holder_count", sa.Integer),
        sa.Column("top10_holder_pct", sa.Float),
        sa.Column("top50_holder_pct", sa.Float),
        sa.Column("is_verified", sa.Boolean),
        sa.Column("is_renounced", sa.Boolean),
        sa.Column("has_proxy", sa.Boolean),
        sa.Column("has_mint_function", sa.Boolean),
        sa.Column("has_blacklist", sa.Boolean),
        sa.Column("buy_tax", sa.Float),
        sa.Column("sell_tax", sa.Float),
        sa.Column("liquidity_locked", sa.Boolean),
        sa.Column("liquidity_lock_duration", sa.Integer),
        sa.Column("lp_burned_pct", sa.Float),
        sa.Column("tx_count_24h", sa.Integer),
        sa.Column("unique_wallets_24h", sa.Integer),
        sa.Column("blockchain", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), server_default="etherscan"),
        sa.Column("extra_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_onchain_data_project_created", "onchain_data", ["project_id", "created_at"])

    op.create_table(
        "whale_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_address", sa.String(255), nullable=False),
        sa.Column("wallet_label", sa.String(255)),
        sa.Column("is_smart_money", sa.Boolean, server_default="false"),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("amount_token", sa.Float),
        sa.Column("amount_usd", sa.Float),
        sa.Column("tx_hash", sa.String(255)),
        sa.Column("blockchain", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("extra_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_whale_activities_project_time", "whale_activities", ["project_id", "timestamp"])
    op.create_index("ix_whale_activities_wallet", "whale_activities", ["wallet_address"])
    op.create_index("ix_whale_activities_action", "whale_activities", ["action"])
    op.create_index("ix_whale_activities_smart_money", "whale_activities", ["is_smart_money"])

    op.create_table(
        "red_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("detected_by", sa.String(100), nullable=False),
        sa.Column("engine", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("evidence", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_red_flags_project_active", "red_flags", ["project_id", "is_active"])
    op.create_index("ix_red_flags_severity", "red_flags", ["severity"])
    op.create_index("ix_red_flags_type", "red_flags", ["flag_type"])

    op.create_table(
        "ai_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("ai_model", sa.String(100), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("full_report", sa.Text),
        sa.Column("recommendation", sa.String(50)),
        sa.Column("ai_score", sa.Float),
        sa.Column("confidence", sa.Float),
        sa.Column("prompt_tokens", sa.Integer),
        sa.Column("completion_tokens", sa.Integer),
        sa.Column("cost_usd", sa.Float),
        sa.Column("structured_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ai_reports_project_type", "ai_reports", ["project_id", "report_type"])
    op.create_index("ix_ai_reports_model", "ai_reports", ["ai_model"])

    op.create_table(
        "alerts_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), server_default="medium"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivered", sa.Boolean, server_default="false"),
        sa.Column("error_message", sa.Text),
        sa.Column("score_at_alert", sa.Float),
        sa.Column("trigger_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_alerts_log_project_type", "alerts_log", ["project_id", "alert_type"])
    op.create_index("ix_alerts_log_channel", "alerts_log", ["channel"])
    op.create_index("ix_alerts_log_sent", "alerts_log", ["sent_at"])

    op.create_table(
        "user_watchlist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_enabled", sa.Boolean, server_default="true"),
        sa.Column("min_score_alert", sa.Float, server_default="70"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_watchlist_user_project", "user_watchlist", ["user_id", "project_id"], unique=True)

    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.String(500)),
        sa.Column("rate_limit_per_minute", sa.Integer, server_default="30"),
        sa.Column("rate_limit_per_day", sa.Integer),
        sa.Column("current_usage_minute", sa.Integer, server_default="0"),
        sa.Column("current_usage_day", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_success", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("error_count", sa.Integer, server_default="0"),
        sa.Column("consecutive_errors", sa.Integer, server_default="0"),
        sa.Column("config", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_data_sources_type", "data_sources", ["source_type"])
    op.create_index("ix_data_sources_active", "data_sources", ["is_active"])

    # Seed default data sources
    op.execute("""
        INSERT INTO data_sources (id, name, source_type, base_url, rate_limit_per_minute, rate_limit_per_day) VALUES
        (uuid_generate_v4(), 'coingecko', 'market', 'https://api.coingecko.com/api/v3', 10, 10000),
        (uuid_generate_v4(), 'dexscreener', 'market', 'https://api.dexscreener.com/latest', 60, NULL),
        (uuid_generate_v4(), 'geckoterminal', 'market', 'https://api.geckoterminal.com/api/v2', 30, NULL),
        (uuid_generate_v4(), 'etherscan', 'onchain', 'https://api.etherscan.io/api', 5, NULL),
        (uuid_generate_v4(), 'bscscan', 'onchain', 'https://api.bscscan.com/api', 5, NULL),
        (uuid_generate_v4(), 'twitter', 'social', 'https://api.twitter.com/2', 15, NULL),
        (uuid_generate_v4(), 'reddit', 'social', 'https://www.reddit.com', 10, NULL),
        (uuid_generate_v4(), 'deepseek', 'ai', 'https://api.deepseek.com/v1', 10, NULL),
        (uuid_generate_v4(), 'gemini', 'ai', 'https://generativelanguage.googleapis.com/v1', 15, NULL)
    """)


def downgrade() -> None:
    # Drop hypertable policies first
    op.execute("SELECT remove_compression_policy('market_data', if_exists => true)")
    op.execute("SELECT remove_compression_policy('social_data', if_exists => true)")
    op.execute("SELECT remove_compression_policy('score_history', if_exists => true)")
    op.execute("SELECT remove_retention_policy('market_data', if_exists => true)")
    op.execute("SELECT remove_retention_policy('social_data', if_exists => true)")

    # Drop tables in reverse order
    op.drop_table("data_sources")
    op.drop_table("user_watchlist")
    op.drop_table("alerts_log")
    op.drop_table("ai_reports")
    op.drop_table("red_flags")
    op.drop_table("whale_activities")
    op.drop_table("onchain_data")
    op.drop_table("score_history")
    op.drop_table("social_data")
    op.drop_table("market_data")
    op.drop_table("token_launches")
    op.drop_table("project_scores")
    op.drop_table("projects")
