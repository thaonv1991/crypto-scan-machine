# Crypto Scan Machine

24/7 cryptocurrency scanning and scoring system with 5 engines:
- Engine 1: New Project Scanner (launchpads, DEX listings)
- Engine 2: Market Data Scanner (price, volume, liquidity)
- Engine 3: Social Intelligence Scanner (Twitter, Telegram, Reddit)
- Engine 4: On-chain Analysis Scanner (whale tracking, smart money)
- Engine 5: AI Analysis Engine (DeepSeek, Gemini, GPT-4o-mini)

## Tech Stack
- Python 3.12+ / FastAPI / Celery
- PostgreSQL 16 + TimescaleDB
- Redis 7 (cache + message broker)
- MinIO (cold storage)
- Docker Compose

## Quick Start

```bash
# Start all services
docker compose up -d

# Run migrations
poetry run alembic upgrade head

# Start API server
poetry run uvicorn app.main:app --reload

# Start Celery worker
poetry run celery -A app.tasks.celery_app worker -l info

# Start Celery beat scheduler
poetry run celery -A app.tasks.celery_app beat -l info
```

## Project Structure
```
app/
├── api/          # FastAPI routes
├── core/         # Config, database, redis, logging
├── models/       # SQLAlchemy ORM models
├── schemas/      # Pydantic schemas
├── services/     # Business logic
│   ├── collectors/   # Data collectors (Engine 1-4)
│   ├── processors/   # Data processors
│   └── scorers/      # Scoring engine (Engine 5)
├── tasks/        # Celery tasks
└── utils/        # Utilities (rate limiter, helpers)
```
