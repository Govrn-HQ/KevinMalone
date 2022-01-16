from bot.common.cache import Cache


# Add in memory implementation
class MockCache(Cache):
    async def get(self, key):
        pass

    async def set(self, key, value):
        pass

    async def delete(self, key):
        pass
