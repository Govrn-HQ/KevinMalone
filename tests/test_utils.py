from datetime import timedelta, time, datetime
from bot.common.cache import Cache
from bot.common.tasks.tasks import Cadence


# Add in memory implementation
class MockCache(Cache):
    def __init__(self):
        self.internal = {}

    async def get(self, key):
        return self.internal.get(key)

    async def set(self, key, value):
        self.internal[key] = value

    async def delete(self, key):
        if self.internal.get(key):
            del self.internal[key]


# This is a continual cadence; it's always running
class MockCadence(Cadence):
    def __init__(self, time_to_run: time):
        self.time_to_run = time_to_run

    def get_timedelta_until_run(self, from_dt: datetime) -> timedelta:
        return timedelta(seconds=-1)

    def get_timedelta_until_next_occurrence(self, from_dt: datetime) -> timedelta:
        return timedelta(seconds=1)

    def get_next_runtime(self) -> datetime:
        return datetime.now() - timedelta(seconds=1)

    def set_time_to_run(self, time_to_run):
        self.time_to_run = time_to_run
