from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.config import read_file


class ReportStep(BaseStep):
    """"""

    name = StepKeys.USER_DISPLAY_CONFIRM.value

    def __init__(self, guild_id):
        self.guild_id = guild_id

    async def send(self, message, user_id):
        channel = message.channel

        airtableLinks = read_file()
        airtableLink = airtableLinks.get(str(self.guild_id))

        sent_message = await channel.send(
            f"Woohoo! Nice job! Community contributions are what keeps"
            " your community thriving 🌞. "
            f"Report you contributions via the form 👉 {airtableLink}",
        )
        return sent_message, None


class Report(BaseThread):
    name = ThreadKeys.REPORT.value

    async def get_steps(self):
        return Step(current=ReportStep(guild_id=self.guild_id)).build()
