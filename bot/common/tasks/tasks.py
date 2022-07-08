import threading
import logging
import asyncio

from abc import ABC, abstractmethod
from datetime import timedelta, datetime, time

from bot.common.tasks.weekly_contributions import send_weekly_contribution_reports
from bot.common.cache import Cache, RedisCache

logger = logging.getLogger(__name__)

TASK_LOOP_INTERVAL_MINUTES = 10
REPORT_LAST_SENT_DATETIME_CACHE_KEY = "contribution_report_last_sent"
DATETIME_CACHE_FMT = "%m/%d/%Y, %H:%M:%S"


class Cadence(ABC):
    # Returns the number of seconds until the task can be run. Negative
    # values reflect that the task is due to fire.
    @abstractmethod
    async def get_timedelta_until_run(self) -> timedelta:
        pass


# associates a callback with a particular Cadence
class Task:
    def __init__(self, cache: Cache, cache_key: str, action, cadence: Cadence):
        self.cache = cache
        self.cache_key = cache_key
        self.action = action
        self.cadence = cadence

    # if the associated cadence is due, run the task
    # return the timedelta until next run
    async def try_run(self) -> timedelta:
        td_until_run = await self.cadence.get_timedelta_until_run()
        if td_until_run < timedelta(0):
            await self.action()
            await self.update_last_run_in_cache()
            td_until_run = await self.cadence.get_timedelta_until_run()
        return td_until_run

    async def update_last_run_in_cache(self):
        await self.cache.set(
            self.cache_key,
            datetime.now().strftime(DATETIME_CACHE_FMT),
        )


# defines a single grouping of tasks which runs in a separate thread
# for periodic execution
class Tasks:
    def __init__(self, cache: Cache):
        self.cache = cache
        self.ticker = threading.Event()
        self.tasks = []

    def _add_task(self, fn, key: str, cadence: Cadence):
        self.tasks.append(Task(self.cache, key, fn, cadence))

    async def _batch_run_tasks(self):
        for task in self.tasks:
            await task.run()

    def task(self, key, cadence: Cadence):
        def decorator(f):
            self._add_task(f, key, cadence)
            return f

    def run(self):
        while not self.ticker.wait(TASK_LOOP_INTERVAL_MINUTES * 60):
            logger.info(f"starting new execution loop of {len(self.tasks)} tasks")
            asyncio.run(self._batch_run_tasks)


class Weekly(Cadence):
    def __init__(
        self, cache: Cache, cache_key: str, day_to_run: int, time_to_run: time
    ):
        self.cache = cache
        self.cache_key = cache_key
        self.day_to_run = day_to_run
        self.time_to_run = time_to_run

    # last_sent should be used to make sure that the bot doesn't
    # always send something on a restart
    async def get_timedelta_until_run(self) -> timedelta:
        last_sent = await self.cache.get(self.cache_key)
        # check that today is the same weekday as the cadence and that
        # the last update was sent 1 week ago
        now: datetime = datetime.now()

        # last_entry does not exist -> return delta to closest ocurrence of next run
        if last_sent is None:
            return self.get_timedelta(now)

        last_sent: datetime = datetime.strptime(last_sent)

        # if the last_sent is on a day that does not match specified weekday,
        # the cadence may have been changed in code, or the task ran late
        # for some reason. log appropriately, return timedelta for next ocurrence
        if last_sent.weekday() != self.day_to_run:
            logger.warning(
                f"Weekly task {self.cache_key} was last run on a different day "
                f"({last_sent.strftime(DATETIME_CACHE_FMT)}) than is specified on "
                f"the task ({self.time_to_run.isoformat()} on {self.day_to_run}th "
                "day of the week)"
            )
            return self.get_timedelta(now)

        return self.get_timedelta_with_last_sent(now, last_sent)

    def get_timedelta(self, now: datetime) -> timedelta:
        if now.weekday() == self.day_to_run:
            if now.time >= self.time_to_run:
                # run immediately
                return timedelta(seconds=-1)
        # wait until the next ocurrence of the specified date and time
        return self.get_timedelta_for_next_occurrence(now)

    def get_timedelta_for_next_occurrence(self, now: datetime) -> timedelta:
        days_until = (self.day_to_run - now.weekday()) % 7
        next_ocurrence = now + timedelta(days=days_until)
        next_ocurrence = datetime.combine(next_ocurrence.date, self.time_to_run)
        return next_ocurrence - now

    def get_timedelta_with_last_sent(
        self, now: datetime, last_sent: datetime
    ) -> timedelta:
        # If the last_sent datetime is today, wait until next ocurrence
        if now.date == last_sent.date:
            return self.get_timedelta_for_next_occurrence(now)
        return self.get_timedelta(now)


# conforms with date.weekday()
class Days:
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


# TASKS

tasks = Tasks(RedisCache())
