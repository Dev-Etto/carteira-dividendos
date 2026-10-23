"""Atualização automática diária enquanto a API estiver rodando."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings
from app.services.sync import start_background_sync


def start_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone="America/Recife")
    s.add_job(start_background_sync, "cron", hour=get_settings().sync_hour, minute=7, id="sync-diario", replace_existing=True)
    s.start()
    return s
