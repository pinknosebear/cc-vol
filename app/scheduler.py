from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.notifications.reminders import schedule_shift_reminders


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    schedule_shift_reminders(scheduler)
    scheduler.start()
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
