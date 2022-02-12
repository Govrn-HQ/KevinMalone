import logging

from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.config import read_file
from bot.common.airtable import (
    get_guild_by_guild_id,
    get_user_record,
    get_contributions,
)
from bot.common.cache import build_congrats_key

logger = logging.getLogger(__name__)


class DisplayPointsStep(BaseStep):
    """Sends a link for a user to report their contributions"""

    name = StepKeys.DISPLAY_POINTS.value

    def __init__(self, guild_id, cache, bot, channel=None):
        self.guild_id = guild_id
        self.cache = cache
        self.bot = bot
        self.channel = channel

    async def send(self, message, user_id):
        channel = self.channel
        if message:
            channel = message.channel

        fields = await get_guild_by_guild_id(self.guild_id)
        base_id = fields.get("fields").get("base_id")
        # get count of uses
        record = await get_user_record(user_id, self.guild_id)
        fields = record.get("fields")
        user_dao_id = fields.get("user_dao_id")
        count = await get_contributions(user_dao_id, base_id)
        # build table

        return None, {"msg": msg}


class Points(BaseThread):
    name = ThreadKeys.POINTS.value

    async def get_steps(self):
        return Step(
            current=PointsStep(guild_id=self.guild_id, cache=self.cache, bot=self.bot)
        ).build()
