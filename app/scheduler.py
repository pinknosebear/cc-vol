from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.start()
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
