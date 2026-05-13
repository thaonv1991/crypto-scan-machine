import asyncio
import logging
from web3 import AsyncWeb3, WebSocketProvider
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Standard Uniswap V2 PairCreated ABI (Used by PancakeSwap, SushiSwap, BaseSwap, etc)
PAIR_CREATED_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token0", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token1", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "pair", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "PairCreated",
        "type": "event"
    }
]

# Supported DEX Factories per chain
CHAINS = {
    "ethereum": {
        "ws_url_env": "ETH_WS_RPC_URL",
        "backup_ws_url_env": "ETH_WS_RPC_URL_BACKUP",
        "default_ws": "wss://mainnet.infura.io/ws/v3/YOUR-PROJECT-ID",
        "factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f", # Uniswap V2
        "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" # WETH
    },
    "bsc": {
        "ws_url_env": "BSC_WS_RPC_URL",
        "backup_ws_url_env": "BSC_WS_RPC_URL_BACKUP",
        "default_ws": "wss://bsc-ws-node.nodedex.io",
        "factory": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73", # PancakeSwap V2
        "weth": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" # WBNB
    },
    "base": {
        "ws_url_env": "BASE_WS_RPC_URL",
        "backup_ws_url_env": "BASE_WS_RPC_URL_BACKUP",
        "default_ws": "wss://base-rpc.publicnode.com",
        "factory": "0x8909Dc15e40173Ff4699343b6eB8132c65e18eC6", # Uniswap V2 on Base
        "weth": "0x4200000000000000000000000000000000000006" # WETH on Base
    }
}

class MultiChainListener:
    """
    World-class Onchain Realtime Listener.
    Listens to multiple chains concurrently.
    """
    def __init__(self, chain_name: str, config: dict, redis_url: str):
        self.chain_name = chain_name
        self.ws_url = getattr(settings, config["ws_url_env"], config["default_ws"])
        self.backup_ws_url = getattr(settings, config.get("backup_ws_url_env", ""), "")
        self.factory_address = config["factory"]
        self.weth_address = config["weth"].lower()
        self.redis_url = redis_url
        self.using_backup = False
        
        self.w3 = AsyncWeb3(WebSocketProvider(self.ws_url))
        self.factory_contract = self.w3.eth.contract(address=self.factory_address, abi=PAIR_CREATED_ABI)

    async def connect(self):
        """Attempts to connect, falls back to Backup RPC if primary fails."""
        if await self.w3.is_connected():
            return True
            
        logger.warning(f"[{self.chain_name.upper()}] Primary WebSocket failed. Attempting Backup...")
        
        if self.backup_ws_url and not self.using_backup:
            self.w3 = AsyncWeb3(WebSocketProvider(self.backup_ws_url))
            self.factory_contract = self.w3.eth.contract(address=self.factory_address, abi=PAIR_CREATED_ABI)
            self.using_backup = True
            
            if await self.w3.is_connected():
                logger.info(f"[{self.chain_name.upper()}] 🟢 Connected to BACKUP Web3 Node: {self.backup_ws_url}")
                return True
                
        logger.error(f"[{self.chain_name.upper()}] ❌ All WebSockets failed to connect.")
        return False

    async def handle_event(self, event):
        """Process the PairCreated event instantly."""
        args = event['args']
        token0 = args['token0']
        token1 = args['token1']
        pair = args['pair']
        
        # Determine which one is the new token
        new_token = token0 if token1.lower() == self.weth_address else token1 if token0.lower() == self.weth_address else None
        
        if new_token:
            logger.info(f"🚀 [{self.chain_name.upper()}] NEW PAIR DETECTED! Pair: {pair} | Token: {new_token}")
            
            token_data = {
                "address": new_token,
                "pair": pair,
                "chain": self.chain_name,
            }
            
            # 🔥 Push directly to Celery for AI Scoring
            from app.tasks.celery_app import celery_app
            celery_app.send_task(
                "app.tasks.scoring_tasks.score_new_realtime_token", 
                kwargs={"token_data": token_data}
            )

    async def listen_loop(self):
        """Main event loop listening to the blockchain with infinite auto-reconnect."""
        while True:
            try:
                if not await self.connect():
                    await asyncio.sleep(5) # Wait 5s before reconnecting
                    continue

                logger.info(f"[{self.chain_name.upper()}] 🎧 Listening for DEX PairCreated events...")
                event_filter = await self.factory_contract.events.PairCreated.create_filter(fromBlock='latest')
                
                while True:
                    new_entries = await event_filter.get_new_entries()
                    for event in new_entries:
                        await self.handle_event(event)
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"[{self.chain_name.upper()}] ❌ Listener Connection Dropped: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
                # Loop restarts, calling connect() again.

async def start_multi_chain_scanner():
    """Entry point: starts concurrent listeners for all configured chains."""
    redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
    
    tasks = []
    for chain, config in CHAINS.items():
        listener = MultiChainListener(chain, config, redis_url)
        tasks.append(asyncio.create_task(listener.listen_loop()))
        
    logger.info(f"🌐 Booting up Multi-Chain Radar for: {', '.join(CHAINS.keys()).upper()}")
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(start_multi_chain_scanner())

