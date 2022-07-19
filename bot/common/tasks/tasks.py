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
    async def get_timedelta_until_run(self, cache: Cache, cache_key: str) -> timedelta:
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
        td_until_run = await self.cadence.get_timedelta_until_run(
            self.cache, self.cache_key
        )
        if td_until_run < timedelta(0):
            await self.action()
            await self.update_last_run_in_cache()
            td_until_run = await self.cadence.get_timedelta_until_run(
                self.cache, self.cache_key
            )
        return td_until_run

    async def update_last_run_in_cache(self):
        await self.cache.set(
            self.cache_key,
            datetime.now().strftime(DATETIME_CACHE_FMT),
        )


# Sets up a batch of tasks and a separate thread to run them.
# Each task is exceuted sequentially in the order it was added.
# A single thread is used to manage the batch of added tasks.
class TaskBatch:
    def __init__(self, cache: Cache, timeout_seconds: int):
        self.cache = cache
        self.timeout_seconds = timeout_seconds
        self.ticker = threading.Event()
        self.thread = threading.Thread(target=self.run)
        self.tasks: list[Task] = []

    def add_task(self, fn, key: str, cadence: Cadence):
        self.tasks.append(Task(self.cache, key, fn, cadence))

    async def _batch_run_tasks(self):
        for task in self.tasks:
            await task.try_run()

    def run(self):
        while not self.ticker.wait(self.timeout_seconds):
            logger.info(f"starting new execution loop of {len(self.tasks)} tasks")
            asyncio.run(self._batch_run_tasks())

    def start(self):
        logger.info(f"starting task batch with {len(self.tasks)} tasks")
        self.thread.start()

    def stop(self):
        logger.info(f"stopping task batch with {len(self.tasks)} tasks..")
        self.ticker.set()
        self.thread.join()
        self.thread = threading.Thread(target=self.run)
        self.ticker.clear()
        logger.info(f"task batch with {len(self.tasks)} stopped")


class Weekly(Cadence):
    def __init__(self, day_to_run: int, time_to_run: time):
        self.day_to_run = day_to_run
        self.time_to_run = time_to_run

    # last_sent should be used to make sure that the bot doesn't
    # always send something on a restart
    async def get_timedelta_until_run(self, cache: Cache, cache_key: str) -> timedelta:
        last_sent = await cache.get(cache_key)
        # check that today is the same weekday as the cadence and that
        # the last update was sent 1 week ago
        now: datetime = datetime.now()

        # last_entry does not exist -> return delta to closest ocurrence of next run
        if last_sent is None:
            return self.get_timedelta(now)

        last_sent: datetime = datetime.strptime(last_sent, DATETIME_CACHE_FMT)

        # if the last_sent is on a day that does not match specified weekday,
        # the cadence may have been changed in code, or the task ran late
        # for some reason. log appropriately, return timedelta for next ocurrence
        if last_sent.weekday() != self.day_to_run:
            logger.warning(
                f"Weekly task {cache_key} was last run on a different day "
                f"({last_sent.strftime(DATETIME_CACHE_FMT)}) than is specified on "
                f"the task ({self.time_to_run.isoformat()} on {self.day_to_run}th "
                "day of the week)"
            )
            return self.get_timedelta(now)

        return self.get_timedelta_with_last_sent(now, last_sent)

    def get_timedelta(self, now: datetime) -> timedelta:
        if now.weekday() == self.day_to_run:
            if now.time() >= self.time_to_run:
                # run immediately
                return timedelta(seconds=-1)
        # wait until the next ocurrence of the specified date and time
        return self.get_timedelta_until_next_occurrence(now)

    def get_timedelta_until_next_occurrence(self, now: datetime) -> timedelta:
        days_until = (self.day_to_run - now.weekday()) % 7
        next_ocurrence = now + timedelta(days=days_until)
        next_ocurrence = datetime.combine(next_ocurrence.date(), self.time_to_run)
        td = next_ocurrence - now
        if td.total_seconds() <= 0:
            td = td + timedelta(days=7)
        return td

    def get_timedelta_with_last_sent(
        self, now: datetime, last_sent: datetime
    ) -> timedelta:
        # If the last_sent datetime is today, wait until next ocurrence
        if now.date() == last_sent.date():
            return self.get_timedelta_until_next_occurrence(now)
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
tasks = TaskBatch(RedisCache(), TASK_LOOP_INTERVAL_MINUTES * 60)


def task(task_collection: TaskBatch, name: str, cadence: Cadence):
    logger.info(f"adding {name} to task list")

    def inner(f):
        task_collection.add_task(f, name, cadence)

    return inner


@task(tasks, "weekly_contribution_report", cadence=Weekly(Days.FRIDAY, time(15, 00)))
async def weekly_contribution_report():
    await send_weekly_contribution_reports()
