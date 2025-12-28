"""
Background worker to monitor device heartbeats and mark devices offline.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import async_session_maker

logger = logging.getLogger(__name__)


async def mark_offline_devices():
    """
    Mark devices as offline if they haven't sent a heartbeat recently.
    
    This runs periodically to catch devices that have gone offline
    without explicitly disconnecting.
    """
    timeout_threshold = datetime.utcnow() - timedelta(seconds=settings.heartbeat_timeout_seconds)
    
    async with async_session_maker() as session:
        # In production, this would be a proper SQLAlchemy update
        # result = await session.execute(
        #     update(Device)
        #     .where(Device.status == 'online')
        #     .where(Device.last_heartbeat < timeout_threshold)
        #     .values(status='offline')
        # )
        # await session.commit()
        # logger.info(f"Marked {result.rowcount} devices as offline")
        pass


async def expire_old_commands():
    """
    Expire commands that have passed their expiry time.
    """
    now = datetime.utcnow()
    
    async with async_session_maker() as session:
        # In production, this would be a proper SQLAlchemy update
        # result = await session.execute(
        #     update(Command)
        #     .where(Command.status == 'pending')
        #     .where(Command.expires_at < now)
        #     .values(status='expired')
        # )
        # await session.commit()
        # logger.info(f"Expired {result.rowcount} commands")
        pass


async def cleanup_old_heartbeats():
    """
    Delete heartbeats older than 30 days to save space.
    """
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    async with async_session_maker() as session:
        # In production, this would be a proper SQLAlchemy delete
        # result = await session.execute(
        #     delete(Heartbeat)
        #     .where(Heartbeat.received_at < cutoff)
        # )
        # await session.commit()
        # logger.info(f"Deleted {result.rowcount} old heartbeats")
        pass


async def heartbeat_monitor_loop():
    """
    Main background loop for heartbeat monitoring.
    
    Runs every 60 seconds to:
    - Mark offline devices
    - Expire old commands
    """
    logger.info("Starting heartbeat monitor...")
    
    while True:
        try:
            await mark_offline_devices()
            await expire_old_commands()
        except Exception as e:
            logger.error(f"Heartbeat monitor error: {e}")
        
        await asyncio.sleep(60)


async def cleanup_loop():
    """
    Background loop for periodic cleanup tasks.
    
    Runs every hour to clean up old data.
    """
    logger.info("Starting cleanup worker...")
    
    while True:
        try:
            await cleanup_old_heartbeats()
        except Exception as e:
            logger.error(f"Cleanup worker error: {e}")
        
        await asyncio.sleep(3600)  # 1 hour

