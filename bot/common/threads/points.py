import json
import logging

from datetime import datetime, timedelta
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
from texttable import Texttable

logger = logging.getLogger(__name__)


def build_table(header, rows):
    table = Texttable()
    r = [header, *rows]
    # breakpoint()
    table.add_rows(r)
    return table


class DisplayPointsStep(BaseStep):
    """Sends a link for a user to report their contributions"""

    name = StepKeys.DISPLAY_POINTS.value

    def __init__(self, guild_id, cache, bot, channel=None, days=None):
        self.guild_id = guild_id
        self.cache = cache
        self.bot = bot
        self.channel = channel
        self.days = days

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
        cache_entry = await self.cache.get(user_id)
        print(user_id)
        days = self.days
        if cache_entry:
            days = json.loads(cache_entry).get("metadata").get("days")
        date = None
        if days != "all":
            date = datetime.now() - timedelta(days=int(days))

        print(days)
        print(date)
        contributions = await get_contributions(user_dao_id, base_id, date)
        # build table
        header = []
        rows = []
        for contribution in contributions:
            fields = contribution.get("fields")
            if not header:
                header = [
                    "Engagement",
                    "status",
                    "Date of Submission",
                    "Date of Engagement",
                    "Points",
                ]
            rows.append(
                [
                    fields.get("Activity"),
                    fields.get("status"),
                    fields.get("Date of Submission"),
                    fields.get("Date of Engagement"),
                    fields.get("Score"),
                ]
            )

        table = build_table(header, rows)
        msg = f"```{table.draw()}```"
        if not self.channel:
            await channel.send(msg)

        return None, {"msg": msg}


class Points(BaseThread):
    name = ThreadKeys.POINTS.value

    async def get_steps(self):
        return Step(
            current=DisplayPointsStep(
                guild_id=self.guild_id, cache=self.cache, bot=self.bot
            )
        ).build()
