import json
import logging
import csv
import io

from datetime import datetime, timedelta
from discord import File
from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
    build_cache_value,
)
from bot.common.threads.shared_steps import EmptyStep
from bot.common.airtable import (
    get_user_record,
    get_contributions,
)
from bot.config import YES_EMOJI, NO_EMOJI
from texttable import Texttable

logger = logging.getLogger(__name__)


def build_table(header, rows):
    table = Texttable()
    r = [header, *rows]
    table.add_rows(r)
    return table


def build_csv(header, rows):
    s = io.StringIO()
    csv.writer(s).writerow(header)
    csv.writer(s).writerows(rows)
    s.seek(0)
    return s


def get_contribution_rows(contributions):
    header = [
        "Engagement",
        "Status",
        "Date of Submission",
        "Date of Engagement",
        "Points",
    ]
    rows = []
    for contribution in contributions:
        fields = contribution.get("fields")
        rows.append(
            [
                fields.get("Activity"),
                fields.get("status"),
                fields.get("Date of Submission"),
                fields.get("Date of Engagement"),
                fields.get("Score"),
            ]
        )
    return [header, rows]


class DisplayPointsStep(BaseStep):
    """Displays points accrued by a given user"""

    name = StepKeys.DISPLAY_POINTS.value
    trigger = True

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

        record = await get_user_record(user_id, self.guild_id)

        if record is None:
            await channel.send(
                "Looks like you're not yet onboarded to the guild! "
                "Complete the intial onboarding before trying to run `/points`"
            )
            return None, None

        fields = record.get("fields")
        user_dao_id = fields.get("user_dao_id")
        cache_entry = await self.cache.get(user_id)
        cache_values = json.loads(cache_entry)
        metadata = cache_values.get("metadata")
        print('points ' + str(user_id))
        days = self.days
        if cache_entry:
            days = metadata.get("days")
        date = None
        if days != "all":
            date = datetime.now() - timedelta(days=int(days or "1"))

        contributions = await get_contributions(user_dao_id, date)
        # [0] is headers, [1] is a list of rows
        contribution_rows = get_contribution_rows(contributions)

        table = build_table(contribution_rows[0], contribution_rows[1])
        msg = f"```{table.draw()}```"
        sent_message = None
        if not self.channel:
            sent_message = await channel.send(content=msg, ephemeral=True)

        metadata.msg = msg
        metadata.contribution_rows = contribution_rows
        cache_values["metadata"] = metadata
        await self.cache.set(
            user_id,
            build_cache_value(**cache_values)
        )

        return sent_message, metadata


class GetContributionsCsvPropmt(BaseStep):
    """Prompts user if they'd like a csv representation of their points"""

    name = StepKeys.POINTS_CSV_PROMPT.value

    def __init__(self, channel=None):
        self.channel = channel

    async def send(self, message, user_id):
        channel = self.channel
        if message:
            channel = message.channel

        sent_message = await channel.send(
            content="Would you like a .csv file of your contributions?",
            ephemeral=True
        )
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)

        return sent_message, None


class GetContributionsCsvPropmtEmoji(BaseStep):
    """Accepts user emoji reaction to if they want a contributions csv"""

    name = StepKeys.POINTS_CSV_PROMPT_EMOJI.value
    emoji = True

    def __init__(self, user_id, cache):
        self.user_id = user_id
        self.cache = cache

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.END.value, None
            return StepKeys.POINTS_CSV_PROMPT_ACCEPT.value, None
        # Throw here?
        raise Exception("Reacted with the wrong emoji")


class GetContributionsCsvPropmtAccept(BaseStep):
    """Creates a contributions csv and sends to the user on emoji acceptance"""

    name = StepKeys.POINTS_CSV_PROMPT_ACCEPT.value

    def __init__(self, cache, channel=None):
        self.cache = cache
        self.channel = channel

    async def send(self, message, user_id):
        channel = self.channel
        if message:
            channel = message.channel

        cache_entry = await self.cache.get(user_id)
        cache_values = json.loads(cache_entry)
        contributions = cache_values.get("metadata").get("contributions")

        csv = build_csv(contributions[0], contributions[1])

        csvFile = File(
            csv,
            str(user_id) + "_points.csv",
            description="A csv file of your points from contributions",
            spoiler=False,
        )

        msg = await channel.send(
            content="Here's your csv!",
            file=csvFile,
            ephemeral=True)

        return msg, None


class Points(BaseThread):
    name = ThreadKeys.POINTS.value

    async def get_steps(self):
        display_points_step = Step(
            current=DisplayPointsStep(
                guild_id=self.guild_id, cache=self.cache, bot=self.bot
            )
        )

        # pass a ref to the DisplayPointsStep so we can retrieve the
        # contributions when generating the csv without going back to
        # airtable. the date range from the DisplayPointsStep is also
        # needed
        points_csv_accept = Step(current=GetContributionsCsvPropmtAccept(self.cache))

        fork_steps = [points_csv_accept, Step(current=EmptyStep())]

        return (
            display_points_step.add_next_step(GetContributionsCsvPropmt())
            .add_next_step(GetContributionsCsvPropmtEmoji(self.user_id, self.cache))
            .fork(fork_steps)
            .build()
        )
