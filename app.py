import os
import logging
from dotenv import load_dotenv
from telegram.ext import Application
import asyncio
from config import Config
from handlers.commands import setup_commands
from handlers.search import setup_search
from handlers.notifications import setup_notifications
from handlers.admin import setup_admin
from scheduler import start_scheduler
from utils.cache import CacheManager
from database.mongodb_manager import MongoDBManager

# Load environment
load_dotenv()

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PriceTrackerBot:
    def __init__(self):
        self.config = Config()
        self.db = MongoDBManager(self.config.mongodb_uris)  # Auto-failover
        self.cache = CacheManager()
        self.app = None
    
    async def start(self):
        """Start bot with all handlers"""
        self.app = Application.builder().token(self.config.telegram_token).build()
        
        # Setup handlers
        setup_commands(self.app, self)
        setup_search(self.app, self)
        setup_notifications(self.app, self)
        setup_admin(self.app, self)
        
        # Start scheduler (10hr checks)
        start_scheduler(self)
        
        logger.info("🤖 Bot starting...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        # Ping endpoint for UptimeRobot
        from fastapi import FastAPI
        fastapi_app = FastAPI()
        
        @fastapi_app.get("/ping")
        async def ping():
            await self.db.ping_current_db()
            return {"status": "alive", "products_tracked": await self.db.get_total_products()}
        
        import uvicorn
        config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=10000)
        server = uvicorn.Server(config)
        await asyncio.gather(server.serve(), self.app.updater.start_polling())

async def main():
    bot = PriceTrackerBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
