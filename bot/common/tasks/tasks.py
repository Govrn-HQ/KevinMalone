from linecache import cache
import threading
import time
import datetime
import logging
import asyncio

from datetime import timedelta, datetime

from bot.common.cache import RedisCache

logger = logging.getLogger(__name__)

TASK_LOOP_INTERVAL_MINUTES = 10
REPORT_LAST_SENT_DATETIME_CACHE_KEY = "contribution_report_last_sent"


class Task:
    def __init__(self, fn, check_run, cadence):
        self.fn = fn
        self.check_run = check_run
        self.cadence = cadence

    async def run(self):
        if await self.check_run(self.cadence):
            await self.fn()


# defines a single grouping of tasks which runs in a separate thread
# for periodic execution
class Tasks:
    def __init__(self):
        self.ticker = threading.Event()
        self.tasks = []

    def _add_task(self, fn, check_run, cadence):
        self.tasks.append(Task(fn, check_run, cadence))

    async def _batch_run_tasks(self):
        for task in self.tasks:
            await task.run()

    def task(self, check_run, cadence: int):
        def decorator(f):
            self._add_task(f, check_run, cadence)
            return f

    def run(self):
        while not self.ticker.wait(TASK_LOOP_INTERVAL_MINUTES * 60):
            logger.info(f"starting new execution loop of {len(self.tasks)} tasks")
            asyncio.run(self._batch_run_tasks)


# Defines a group of commonly used predicates for determining if the task should
# run at the supplied datetime
class Cadences:
    cache = RedisCache()

    # Requires cache to determine if report has already been sent
    async def once_weekly(weekday: int) -> bool:
        last_sent = await Cadences.cache.get(REPORT_LAST_SENT_DATETIME_CACHE_KEY)
        # check that today is the same weekday as the cadence and that
        # the last update was sent 1 week ago
        now = datetime.now()
        td: timedelta = (
            None if last_sent is None else now - datetime.strptime(last_sent)
        )
        if td.days >= 7 and now.date().weekday() == weekday:
            await Cadences.cache.set(
                REPORT_LAST_SENT_DATETIME_CACHE_KEY, now.strftime("%m/%d/%Y, %H:%M:%S")
            )
            return True
        return False


# conforms with date.weekday()
class Days:
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


tasks = Tasks()


# Want the report to be sent weekly, 5pm on fridays

# sol 1: print report, sleep until next friday
# downside: a report would be sent everyime the bot is upgraded
# downside: reports would be skipped potentially if timing wasn't spot on

# sol 2: check cache for last report. if it's past 5pm friday, and we haven't sent the
#   report yet, do so, and update the cache


@tasks.task(Cadences.once_weekly, Days.FRIDAY)
def weekly_report():
    pass
