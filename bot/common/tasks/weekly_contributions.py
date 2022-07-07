import io
import logging
from typing import Dict
import pandas as pd
from datetime import datetime
from discord import EmbedField, File, Embed
from pyairtable import Table
from pyairtable.formulas import match

from bot.common.airtable import (
    get_guild_by_guild_id,
    get_guild_id_by_guild_name,
    get_activity_name,
    get_member_name,
    get_discord_id_from_user_record,
)

from bot import constants
from bot.common.bot.bot import bot
from bot.config import AIRTABLE_BASE, AIRTABLE_KEY, INFO_EMBED_COLOR

logger = logging.getLogger(__name__)

active_guilds = ["Govrn"]


async def send_weekly_contribution_reports():
    # retrieve the reporting channel from airtable
    govrn_guild_id = constants.Bot.govrn_guild_id
    govrn_guild = await get_guild_by_guild_id(govrn_guild_id)
    report_channel_id = govrn_guild.get("fields").get("report_channel")

    # if none is specified, log message and return
    if report_channel_id is None or report_channel_id == "":
        logger.info(f"report_channel is not specified for guild {govrn_guild_id}")
        return

    # get guilds for reporting
    guilds_to_report = get_guilds_to_report()

    # generate reports
    reports = generate_contribution_reports(guilds_to_report)
    formatted_date = get_formatted_date()
    guilds_to_report_field = EmbedField(
        name="Reporting guilds", value=", ".join(guilds_to_report)
    )

    embed_description = (
        "Reporting on the contributions submitted for each active"
        " guild onboarded to Govrn are attached below as .csv files"
    )

    embed = Embed(
        colour=INFO_EMBED_COLOR,
        title=f"Weekly contribution report for {formatted_date}",
        description=embed_description,
        fields=[guilds_to_report_field],
    )

    channel = bot.get_channel(report_channel_id)
    # print message for series of reports
    for guild, report in reports:
        await channel.send(content=guild, file=report)


# helper functions

# TODO: config? airtable query?
def get_guilds_to_report():
    return active_guilds


# TODO: asyncify
def create_guild_dataframe(guild_name) -> pd.DataFrame:
    """Returns the community's weekly csv given the guild name."""

    # translate guild name to guild id
    guild_id = get_guild_id_by_guild_name(guild_name)

    # filter Activity History Staging by guild id
    table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Activity History Staging")
    # records = table.all(formula=match({"Guild": guild_id}))
    records = table.all(formula=match({"reportedToGuild": guild_id}))

    # convert records from json to df
    df_rows = []
    df_index = []

    for rec in records:  # this part can be optimized for speed later
        df_rows.append(rec["fields"])
        df_index.append(rec["id"])
    df = pd.DataFrame(df_rows, index=df_index)

    df = df[
        [
            "ActivityType",
            "Description",
            "status",
            "Member",
            "member_globalID",
            "DateOfEngagement",
            "DateofSubmission",
        ]
    ]

    # map linked records
    # TODO: These should be rewritten so the lambdas are async/nonblocking
    df["ActivityType"] = df.apply(
        lambda x: get_activity_name(x["ActivityType"][0]), axis=1
    )
    df["Member"] = df.apply(lambda x: get_member_name(x["Member"][0]), axis=1)
    df["member_globalID"] = df.apply(
        lambda x: get_discord_id_from_user_record(x["member_globalID"][0]), axis=1
    )

    # rename columns
    df = df.rename(
        columns={
            "ActivityType": "Engagement",
            "status": "Status",
            "Member": "User",
            "member_globalID": "Discord_ID",
            "DateofSubmission": "Date of Submission",
            "DateOfEngagement": "Date of Engagement",
        }
    )

    # sort by descending date of engagement
    df = df.sort_values(by=["Date of Engagement"], ascending=False)

    # drop airtable record index
    # df = df.reset_index(drop=True)

    return df


def get_formatted_date():
    # convert to csv
    date = datetime.today()
    date_reformat = (
        str(date.year)[-2:]
        + "_"
        + str(date.month).zfill(2)
        + "_"
        + str(date.day).zfill(2)
    )
    return date_reformat


def generate_contribution_reports(guilds_to_report) -> Dict[str, File]:
    reports = {}
    for guild in guilds_to_report:
        # generate dataframe
        df = create_guild_dataframe(guild)
        date_reformat = get_formatted_date()

        csv_name = "{}_{}.csv".format(guild, date_reformat)

        s = io.StringIO()
        s.write(df.to_string())
        s.seek(0)

        csv_file = File(
            fp=s,
            filename=csv_name,
            description=f"{date_reformat} weekly contribution report for {guild}",
        )

        reports[csv_name] = csv_file

    return reports
