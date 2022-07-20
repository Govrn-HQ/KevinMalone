import pytest
import time as systime

from datetime import datetime, time, timedelta

from bot.common.tasks.tasks import (
    DATETIME_CACHE_FMT, TaskBatch, Weekly, task
)
from bot.common.tasks.weekly_contributions import create_guild_dataframe
from tests.test_utils import MockCache, MockCadence


@pytest.mark.tasks
def test_add_task():
    task_batch = TaskBatch(MockCache(), 60 * 60)

    @task(task_batch, "empty_task", MockCadence(time(00, 00)))
    def empty_task():
        pass

    assert len(task_batch.tasks) == 1


@pytest.mark.tasks
@pytest.mark.asyncio
async def test_add_and_run_task():
    task_batch = TaskBatch(MockCache(), 60 * 60)
    has_run = False

    @task(task_batch, "empty_task", MockCadence(time(00, 00)))
    async def empty_task():
        nonlocal has_run
        has_run = True

    await task_batch._batch_run_tasks()
    assert has_run


@pytest.mark.tasks
def test_start_task_batch():
    task_batch = TaskBatch(MockCache(), 1)
    acc = 0

    @task(task_batch, "empty_task", MockCadence(time(00, 00)))
    async def empty_task():
        nonlocal acc
        acc += 1

    assert acc == 0
    task_batch.start()
    systime.sleep(5)
    assert acc > 0
    task_batch.stop()


@pytest.mark.tasks
def test_start_stop_task_batch():
    task_batch = TaskBatch(MockCache(), 1)
    acc = 0

    @task(task_batch, "empty_task", MockCadence(time(00, 00)))
    async def empty_task():
        nonlocal acc
        acc += 1

    assert acc == 0
    task_batch.start()
    systime.sleep(5)
    task_batch.stop()
    assert acc > 0

    latch_acc = acc
    systime.sleep(5)
    assert latch_acc == acc

    task_batch.start()
    systime.sleep(5)
    task_batch.stop()
    assert acc > latch_acc


@pytest.mark.cadence
def test_weekly_cadence():
    now = datetime.now()
    # create a weekly cadence that runs on the current weekday, 
    # one hour from the current time
    weekday = now.weekday()
    time_plus: time = (now + timedelta(hours=1)).time()
    time_minus: time = (now - timedelta(hours=1)).time()

    cadence = Weekly(weekday, time_plus)

    # check that the timedelta to next occurrence is under 1h
    td = cadence.get_timedelta_until_next_occurrence(now)
    # assert the timedelta is between 0 and 1h
    assert td.total_seconds() <= 60 * 60
    assert td.total_seconds() > 0

    cadence = Weekly(weekday, time_minus)
    td = cadence.get_timedelta_until_next_occurrence(now)
    # assert the timedelta is between 6 and 7 days
    assert td.total_seconds() <= 7 * 24 * 60 * 60
    assert td.total_seconds() > 6 * 24 * 60 * 60


@pytest.mark.cadence
@pytest.mark.asyncio
async def test_weekly_cadence_with_last_run():
    now = datetime.now()
    cache = MockCache()

    # create a weekly cadence that runs on the current weekday,
    # one hour from the current time
    weekday = now.weekday()
    time_minus: time = (now - timedelta(hours=1)).time()

    cadence = Weekly(weekday, time_minus)

    # nothing exists in the cache, so this should run immediately
    td = await cadence.get_timedelta_until_run(cache, "empty_cache_key")

    assert td.total_seconds() == -1

    # set the last run time in the cache to
    last_run_str = now.strftime(DATETIME_CACHE_FMT)
    await cache.set("last_run", last_run_str)

    td = await cadence.get_timedelta_until_run(cache, "last_run")

    # assert td is next week, since we've mocked the cache to
    # indicate the task has already been run today
    assert td.total_seconds() <= 7 * 24 * 60 * 60
    assert td.total_seconds() > 6 * 24 * 60 * 60


@pytest.mark.asyncio
@pytest.mark.weekly_report
@pytest.mark.skip(reason="gh actions env is not populated with data")
async def test_weekly_report():
    df = await create_guild_dataframe(3)
    assert df
