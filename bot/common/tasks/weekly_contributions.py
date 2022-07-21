import asyncio
import io
import logging
from typing import Dict, Union
import pandas as pd
from datetime import datetime
from discord import EmbedField, File, Embed

from bot.common.airtable import (
    get_guild_by_guild_id,
)
from bot.common.graphql import (
    get_contributions_for_guild,
)

from bot import constants
from bot.config import INFO_EMBED_COLOR

logger = logging.getLogger(__name__)

active_guild_ids = [3]


async def save_weekly_contribution_reports():
    # get guilds for reporting
    guilds_to_report = get_guilds_to_report()
    reports = await generate_contribution_reports(
        guilds_to_report,
        local_csv=True
    )
    for csv_name, csv in reports:
        logger.info(f"saving report {csv_name}...")
        with open(csv_name, 'w') as f:
            print(csv.getvalue(), file=f)
        logger.info(f"done saving report {csv_name}")


async def send_weekly_contribution_reports(bot):
    # retrieve the reporting channel from airtable
    govrn_guild_id = constants.Bot.govrn_guild_id
    govrn_guild = await get_guild_by_guild_id(govrn_guild_id)
    # TODO
    report_channel_id = govrn_guild.get("fields").get("report_channel")

    # if none is specified, log message and return
    if report_channel_id is None or report_channel_id == "":
        logger.info(f"report_channel is not specified for guild {govrn_guild_id}")
        return

    # get guilds for reporting
    guilds_to_report = get_guilds_to_report()

    reports = await generate_contribution_reports(guilds_to_report)

    channel = bot.get_channel(report_channel_id)
    await send_reports(channel, guilds_to_report, reports)


# helper functions
async def send_reports(channel, guilds_to_report, reports):
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

    await channel.send(embed=embed)

    # print message for series of reports
    for guild, report in reports:
        await channel.send(content=guild, file=report)


# TODO: config? airtable query?
def get_guilds_to_report():
    return active_guild_ids


async def generate_contribution_reports(guilds_to_report, local_csv=False) -> Dict[str, Union[File, io.StringIO]]:
    reports = {}
    for guild in guilds_to_report:
        # generate dataframe
        df = await create_guild_dataframe(guild)
        date_reformat = get_formatted_date()

        csv_name = "{}_{}.csv".format(guild, date_reformat)

        s = io.StringIO()
        df.to_csv(s, index=False)
        s.seek(0)

        # just store the string buffer if we're generating local
        # reports on disk
        if local_csv:
            reports[csv_name] = s
            continue

        csv_file = File(
            fp=s,
            filename=csv_name,
            description=f"{date_reformat} weekly contribution report for {guild}",
        )

        reports[csv_name] = csv_file

    return reports


async def create_guild_dataframe(guild_id: int) -> pd.DataFrame:
    """Returns the community's weekly csv given the guild name."""
    logger.info(f"retrieving contributions for guild {guild_id}...")

    records = await get_contributions_for_guild(
        guild_id, user_discord_id=None, after_date=None
    )
    
    logger.info(f"done retrieving contributions for guild {guild_id}")

    # convert records from json to df
    df_rows = []
    df_index = []

    logger.info(f"constructing dataframe for guild {guild_id}...")

    for rec in records:  # this part can be optimized for speed later
        df_rows.append(rec)
        df_index.append(rec["id"])
    df = pd.DataFrame(df_rows, index=df_index)

    df = df[
        [
            "activity_type",
            "details",
            "status",
            "user",
            "date_of_engagement",
            "date_of_submission",
        ]
    ]

    df["activity_type"] = df.apply(lambda x: x["activity_type"]["name"], axis=1)
    df["discord_id"] = df.apply(
        lambda x: x["user"]["discord_users"][0]["discord_id"], axis=1
    )
    df["user"] = df.apply(lambda x: x["user"]["display_name"], axis=1)
    df["status"] = df.apply(lambda x: x["status"]["name"], axis=1)

    # rename columns
    df = df.rename(
        columns={
            "activity_type": "Engagement",
            "details": "Description",
            "status": "Status",
            "user": "User",
            "discord_id": "Discord_ID",
            "date_of_submission": "Date of Submission",
            "date_of_engagement": "Date of Engagement",
        }
    )

    # sort by descending date of engagement
    df = df.sort_values(by=["Date of Engagement"], ascending=False)

    logger.info(f"done constructing dataframe for guild {guild_id}")

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


if __name__ == "__main__":
    logger.info("file directly invoked. saving weekly contributions locally...")
    asyncio.run(save_weekly_contribution_reports())
    logger.info("done saving weekly contribution reports locally!")
