import json
import logging
import csv
import io
import discord

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
from bot.common.airtable import (
    get_user_record,
    get_contributions,
)
from bot.config import (
    YES_EMOJI,
    NO_EMOJI,
    INFO_EMBED_COLOR,
)
from texttable import Texttable

logger = logging.getLogger(__name__)


def build_table(header, rows):
    table = Texttable()
    r = [header, *rows]
    table.add_rows(r)
    return table


def build_csv_file(header, rows, user_id):
    s = io.StringIO()
    csv.writer(s).writerow(header)
    csv.writer(s).writerows(rows)
    s.seek(0)

    csvFile = File(
        s,
        str(user_id) + "_points.csv",
        description="A csv file of your points from contributions",
        spoiler=False,
    )
    return csvFile


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

    def __init__(self, guild_id, cache, bot, context, days=None):
        self.guild_id = guild_id
        self.cache = cache
        self.bot = bot
        self.context = context
        self.days = days
        self.end_flow = False

    async def send(self, message, user_id):
        # message is none in server; message is not none in DMs from
        # guild select flow
        is_in_dms = message is not None
        # end flow in control hook if this is in a discord server
        self.end_flow = not is_in_dms

        record = await get_user_record(user_id, self.guild_id)
        logger.info(
            "user_id "
            + str(user_id)
            + "guild id "
            + str(self.guild_id)
            + " records: "
            + json.dumps(record)
        )
        if record is None:
            self.end_flow = True
            content = "Looks like you're not yet onboarded to the guild! "
            "Complete the intial onboarding before trying to run `/points`"
            if is_in_dms:
                return await message.channel.send(content), None
            else:
                return (
                    await self.context.response.send_message(
                        content=content, ephemeral=True
                    ),
                    None,
                )

        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            title="Your points!",
            description="Below is a table representation of  "
            "the points you've accrued from your contributions! ",
        )

        if is_in_dms:
            await message.channel.send(embed=embed)
        else:
            await self.context.response.send_message(embed=embed, ephemeral=True)

        fields = record.get("fields")
        global_id = fields.get("global_id")
        cache_entry = await self.cache.get(user_id)
        cache_values = json.loads(cache_entry)
        metadata = cache_values.get("metadata")
        print("points " + str(user_id))
        days = self.days
        if cache_entry:
            days = metadata.get("days")
        date = None
        td = (
            timedelta(weeks=52 * 20)
            if days == "all"
            else timedelta(days=int(days or "1"))
        )
        date = datetime.now() - td

        contributions = await get_contributions(global_id, date)
        # [0] is headers, [1] is a list of rows
        contribution_rows = get_contribution_rows(contributions)

        table = build_table(contribution_rows[0], contribution_rows[1])
        msg = f"```{table.draw()}```"
        sent_message = None
        metadata["msg"] = msg

        if is_in_dms:
            sent_message = await message.channel.send(msg)
        else:
            csv_file = build_csv_file(
                contribution_rows[0], contribution_rows[1], user_id
            )
            followup = self.context.interaction.followup
            sent_message = await followup.send(
                content=msg, ephemeral=True, file=csv_file
            )
            return sent_message, metadata

        metadata["contribution_rows"] = contribution_rows
        cache_values["metadata"] = metadata
        await self.cache.set(user_id, build_cache_value(**cache_values))

        return sent_message, metadata

    async def control_hook(self, message, user_id):
        if self.end_flow:
            return StepKeys.END.value


class GetContributionsCsvPropmt(BaseStep):
    """Prompts user if they'd like a csv representation of their points"""

    name = StepKeys.POINTS_CSV_PROMPT.value

    async def send(self, message, user_id):
        sent_message = await message.channel.send(
            content="Would you like a .csv file of your contributions?"
        )
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)

        return sent_message, None


class GetContributionsCsvPropmtEmoji(BaseStep):
    """Accepts user emoji reaction to if they want a contributions csv"""

    name = StepKeys.POINTS_CSV_PROMPT_EMOJI.value
    emoji = True

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

    def __init__(self, cache):
        self.cache = cache

    async def send(self, message, user_id):
        cache_entry = await self.cache.get(user_id)
        cache_values = json.loads(cache_entry)
        contributions = cache_values.get("metadata").get("contribution_rows")

        csv_file = build_csv_file(contributions[0], contributions[1], user_id)

        msg = await message.channel.send(content="Here's your csv!", file=csv_file)

        return msg, None


class Points(BaseThread):
    name = ThreadKeys.POINTS.value

    async def get_steps(self):
        display_points_step = Step(
            current=DisplayPointsStep(
                guild_id=self.guild_id,
                cache=self.cache,
                bot=self.bot,
                context=self.context,
            )
        )

        points_csv_accept = Step(current=GetContributionsCsvPropmtAccept(self.cache))

        return (
            display_points_step.add_next_step(GetContributionsCsvPropmt())
            .add_next_step(GetContributionsCsvPropmtEmoji())
            .add_next_step(points_csv_accept)
            .build()
        )
