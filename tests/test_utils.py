from bot.common.cache import Cache


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
