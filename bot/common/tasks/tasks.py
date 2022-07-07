import threading
import logging
import asyncio

from bot.common.cache import Cache, RedisCache
from abc import ABC, abstractmethod
from datetime import timedelta, datetime, time

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


class Cadence(ABC):

    # Returns the number of seconds until the task can be run. Negative
    # values reflect that the task is due to fire.
    @abstractmethod
    async def timedelta_until_run(self) -> timedelta:
        pass

    async def update_last_run_in_cache(self):
        await self.cache.set(
            REPORT_LAST_SENT_DATETIME_CACHE_KEY,
            datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        )


class Weekly(Cadence):
    def __init__(self, cache: Cache, cache_key: str, day_to_run: int, time_to_run: time):
        self.cache = cache
        self.cache_key = cache_key
        self.day_to_run = day_to_run
        self.time_to_run = time_to_run

    # last_sent should be used to make sure that the bot doesn't 
    # always send something on a restart
    async def timedelta_until_run(self) -> timedelta:
        last_sent = await self.cache.get(self.cache_key)
        # check that today is the same weekday as the cadence and that
        # the last update was sent 1 week ago
        now: datetime = datetime.now()

        # last_entry does not exist -> return delta to closest ocurrence of day to run, time
        if last_sent is None:
            if now.weekday() == self.day_to_run:
                # run immediately
                return timedelta(seconds=-1)
            # return the timedelta for the next occurrence of the day and time to run

        # case 1: last_entry exists -> return delta to next ocurrence of day to run, time to run
        # do we need handling of last_entries on odd days?

        # if there is no last_sent entry in the cache, then wait for the
        # next ocurrence of the day + time to run

        td: timedelta = (
            None if last_sent is None else now - datetime.strptime(last_sent)
        )
        if td.days >= 7 and now.date().weekday() == self.day_to_run:
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


@tasks.task(Cadences.weekly, Days.FRIDAY)
def weekly_report():
    pass
