from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.config import read_file
from bot.common.airtable import get_guild_by_guild_id, get_contribution_count
from bot.common.cache import build_congrats_key
from bot.common.bot.bot import bot


class ReportStep(BaseStep):
    """"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value

    def __init__(self, guild_id, cache):
        self.guild_id = guild_id
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel

        airtableLinks = read_file()
        airtableLink = airtableLinks.get(str(self.guild_id))

        sent_message = await channel.send(
            f"Woohoo! Nice job! Community contributions are what keeps"
            " your community thriving 🌞. "
            f"Report you contributions via the form 👉 {airtableLink}",
        )
        # Check cache that user hasn't sent in the last hour
        if not self.cachel.get(build_congrats_key(user_id)):
            fields = await get_guild_by_guild_id(self.guild_id)
            congrats_channel_id = fields.get("fields").get("congrats_chanel_id")
            base_id = fields.get("fields").get("base_id")
            channel = await bot.get_channel(congrats_channel_id)
            user = await bot.get_user(user_id)
            # get count of uses
            count = await get_contribution_count(user_id, base_id)
            await channel.send(
                f"Congrats {user.display_name} for reporting {count} engagements this week!"
            )

            # bot get channel
            # Send congrats mesage
        return sent_message, None


class Report(BaseThread):
    name = ThreadKeys.REPORT.value

    async def get_steps(self):
        return Step(current=ReportStep(guild_id=self.guild_id, cache=cache)).build()
