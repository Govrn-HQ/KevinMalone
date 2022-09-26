import logging
import datetime
from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.config import REPORTING_FORM_FMT
import bot.common.graphql as gql
from bot.common.cache import build_congrats_key

logger = logging.getLogger(__name__)


class ReportStep(BaseStep):
    """Sends a link for a user to report their contributions"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value

    def __init__(self, guild_id, cache, bot, channel=None):
        self.guild_id = guild_id
        self.cache = cache
        self.bot = bot
        self.channel = channel

    async def send(self, message, user_id):
        channel = self.channel
        if message and message.channel:
            channel = message.channel

        guild = await gql.get_guild_by_discord_id(self.guild_id)
        link = (
            REPORTING_FORM_FMT % guild["id"]
        )

        msg = (
            f"Woohoo! Nice job! Community contributions are what keeps"
            " your community thriving 🌞. "
            f"Report your contributions via the form 👉 {link}"
        )
        if message:
            await channel.send(msg)

        congrats_key = build_congrats_key(user_id)

        if not await self.cache.get(congrats_key):
            congrats_channel_id = guild.get("congrats_channel")
            if not congrats_channel_id:
                logger.warn("No congrats channel id!")
                return None, {"msg": msg}

            channel = self.bot.get_channel(int(congrats_channel_id))
            user = self.bot.get_user(user_id)
            # get count of uses
            one_week = datetime.datetime.now() - datetime.timedelta(weeks=1)
            contributions = await gql.get_contributions(
                guild_id=guild.get("id"),
                user_discord_id=user_id,
                after_date=one_week.isoformat())
            if len(contributions) > 0:
                await channel.send(
                    f"Congrats {user.display_name} for reporting {len(contributions)} "
                    "engagements this week!"
                )
                await self.cache.set(
                    congrats_key, "True", ex=60 * 60
                )  # Expires in an hour

        return None, {"msg": msg}


class Report(BaseThread):
    name = ThreadKeys.REPORT.value

    async def get_steps(self):
        return Step(
            current=ReportStep(guild_id=self.guild_id, cache=self.cache, bot=self.bot)
        ).build()
