import logging

from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.config import REPORTING_FORM_FMT
from bot.common.graphql import (
    get_guild_by_id,
)
from bot.common.cache import build_congrats_key

logger = logging.getLogger(__name__)


class ReportStep(BaseStep):
    """Sends a link for a user to report their contributions"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value

    def __init__(self, guild_id, cache, bot, channel=None, reporting_link=None):
        self.guild_id = guild_id
        self.cache = cache
        self.bot = bot
        self.channel = channel
        self.reporting_link = reporting_link

    async def send(self, message, user_id):
        channel = self.channel
        if message:
            channel = message.channel

        link = (
            REPORTING_FORM_FMT % self.guild_id
            if self.reporting_link is None
            else self.reporting_link
        )

        msg = (
            f"Woohoo! Nice job! Community contributions are what keeps"
            " your community thriving 🌞. "
            f"Report your contributions via the form 👉 {link}"
        )
        if message:
            await channel.send(msg)

        # TODO: this will break because of self.guild_id and db changes
        if not await self.cache.get(build_congrats_key(user_id)):
            fields = await get_guild_by_id(self.guild_id)
            congrats_channel_id = fields.get("congrats_channel_id")
            if not congrats_channel_id:
                logger.warn("No congrats channel id!")
                return None, {"msg": msg}

            # channel = self.bot.get_channel(int(congrats_channel_id))
            # user = self.bot.get_user(user_id)
            # # get count of uses
            # record = await fetch_user_by_discord_id(user_id, self.guild_id)
            # fields = record.get("fields")
            # # TODO: Pro-309
            # # count = await get_contribution_count(fields.get("id"))
            # if count > 0:
            #     await channel.send(
            #         f"Congrats {user.display_name} for reporting {count} "
            #         "engagements this week!"
            #     )
            #     await self.cache.set(
            #         build_congrats_key(user_id), "True", ex=60 * 60
            #     )  # Expires in an hour

        return None, {"msg": msg}


class Report(BaseThread):
    name = ThreadKeys.REPORT.value

    async def get_steps(self):
        return Step(
            current=ReportStep(guild_id=self.guild_id, cache=self.cache, bot=self.bot)
        ).build()


async def get_reporting_link(guild_discord_id):
    guild = await get_guild_by_id(guild_discord_id)
    guild_id = guild.get("id")
    return REPORTING_FORM_FMT % guild_id
