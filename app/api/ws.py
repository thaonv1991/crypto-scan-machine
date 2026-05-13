import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from app.core.redis import redis_client

logger = structlog.get_logger()
router = APIRouter()

# Store active websocket connections
active_connections = set()

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("websocket.connected", active_connections=len(active_connections))
    
    try:
        # Create a redis pubsub channel listener
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("new_alerts")
        
        # Task to listen to Redis and push to WS
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.error("websocket.send_error", error=str(e))
                        
        redis_task = asyncio.create_task(listen_redis())
    except Exception as e:
        logger.warning("Redis not available, falling back to local simulation mode for WebSocket.")
        # Fallback for Windows without Docker
        async def simulate_live_data():
            import random
            while True:
                await asyncio.sleep(4.5)
                newScore = random.randint(5, 100)
                risk = 'SAFE' if newScore >= 80 else 'WARNING' if newScore >= 40 else 'DANGER'
                rString = f"0x{random.randint(1000, 9999)}"
                data = {
                    "id": f"local-{random.randint(1000, 99999)}",
                    "name": f"Local Token {rString}",
                    "symbol": f"L{rString[:3]}",
                    "chain": random.choice(["Ethereum", "BSC", "Base", "Solana"]),
                    "price": f"${random.uniform(0.1, 100):.4f}",
                    "volume": "$0.0M",
                    "liquidity": f"${random.uniform(0.1, 5):.1f}M",
                    "score": newScore,
                    "risk": risk,
                    "flags": ["HONEYPOT", "BLACKLIST"] if risk == 'DANGER' else ["MINTABLE"] if risk == 'WARNING' else [],
                    "timeLabel": "Just now",
                    "discoveredMinutes": 0,
                    "ageLabel": "0m",
                    "ageMinutes": 0,
                    "isNew": True
                }
                try:
                    await websocket.send_json(data)
                except:
                    break
                    
        redis_task = asyncio.create_task(simulate_live_data())
        pubsub = None
        
    try:
        # Keep connection alive and handle client disconnects
        while True:
            await websocket.receive_text() # Client can send ping
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("websocket.disconnected", active_connections=len(active_connections))
    except Exception as e:
        logger.error("websocket.error", error=str(e))
        if websocket in active_connections:
            active_connections.remove(websocket)
    finally:
        redis_task.cancel()
        if pubsub:
            await pubsub.unsubscribe("new_alerts")
            await pubsub.close()
