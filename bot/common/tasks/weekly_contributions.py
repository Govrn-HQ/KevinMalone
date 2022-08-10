import asyncio
import os
import io
import logging
from typing import Dict, Union
import pandas as pd
from datetime import datetime, timedelta
from discord import EmbedField, File, Embed, Bot

from bot.common.graphql import (
    get_contributions_for_guild,
    get_guild_by_discord_id,
    get_guilds,
)

from bot import constants
from bot.config import INFO_EMBED_COLOR

logger = logging.getLogger(__name__)


async def save_weekly_contribution_reports():
    # get guilds for reporting
    guilds_to_report = await get_guilds_to_report()
    reports = await generate_guild_contribution_reports(
        guilds_to_report, local_csv=True
    )
    all_contributions_name = "all_contributions"
    all_contributions_df = await create_all_contributions_dataframe()
    all_contributions_csv = await write_dataframe_to_csv(
        all_contributions_df, all_contributions_name, description="", local_csv=True
    )
    reports[all_contributions_name] = all_contributions_csv

    directory = "./reports/"
    if not os.path.exists(directory):
        os.mkdir(directory)
    formatted_date = get_formatted_date()
    for csv_name, csv in reports.items():
        path = f"{directory}{csv_name}_{formatted_date}.csv"
        logger.info(f"saving report {path}...")
        with open(path, "w") as f:
            print(csv.getvalue(), file=f)
        logger.info(f"done saving report {path}")


async def send_weekly_contribution_reports(bot: Bot, reporting_channel_id: str = None):
    # retrieve the reporting channel
    govrn_guild_discord_id = constants.Bot.govrn_guild_id
    govrn_guild = await get_guild_by_discord_id(govrn_guild_discord_id)

    if reporting_channel_id is None:
        reporting_channel_id = govrn_guild.get("contribution_reporting_channel")
        # if none is specified, log message and return
        if reporting_channel_id is None or reporting_channel_id == "":
            logger.info(
                f"report_channel is not specified for guild {govrn_guild_discord_id}"
            )
            return

    # get guilds for reporting
    guilds_to_report = await get_guilds_to_report()

    reports = await generate_guild_contribution_reports(guilds_to_report)

    channel = bot.get_channel(int(reporting_channel_id))
    await send_reports(channel, guilds_to_report, reports)


# helper functions
async def send_reports(channel, guilds_to_report, reports):
    guild_names = [guild["name"] for guild in guilds_to_report]
    formatted_date = get_formatted_date()
    guilds_to_report_field = EmbedField(
        name="Reporting guilds", value=", ".join(guild_names)
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
    for guild, report in reports.items():
        await channel.send(content=guild, file=report)


async def get_guilds_to_report():
    # query all guilds
    guilds = await get_guilds()
    return guilds
    # return [
    #     (1, "Rolf's Server"),
    #     (2, "Ludium"),
    #     (3, "Boys Club"),
    #     (4, "Education DAO"),
    #     (5, "DreamDAO"),
    #     (6, "GDS"),
    #     (7, "PadawanDAO"),
    #     (8, "Dynamiculture"),
    #     (9, "MGD"),
    #     (10, "Keating"),
    #     (11, "RaidGuild"),
    #     (12, "SporeDAO"),
    #     (13, "Govrn"),
    #     (14, "ATS"),
    #     (15, "Daohaus"),
    # ]


async def write_dataframe_to_csv(
    dataframe, name, description, local_csv=False
) -> Union[File, io.StringIO]:
    if dataframe is None:
        return (None, None)

    s = io.StringIO()
    dataframe.to_csv(s, index=False)
    s.seek(0)

    # just store the string buffer if we're generating local
    # reports on disk
    if local_csv:
        return s

    csv_file = File(fp=s, filename=name, description=description)

    return csv_file


async def generate_guild_contribution_reports(
    guilds_to_report, local_csv=False
) -> Dict[str, Union[File, io.StringIO]]:
    reports = {}
    for guild in guilds_to_report:
        guild_id = guild["id"]
        guild_name = guild["name"]
        # generate dataframe
        df = await create_guild_dataframe(guild_id)
        date_reformat = get_formatted_date()

        if df is None:
            continue

        description = f"{date_reformat} weekly contribution report for {guild_name}"

        reports[guild_name] = await write_dataframe_to_csv(
            df, guild_name, description, local_csv
        )

    return reports


async def create_all_contributions_dataframe() -> pd.DataFrame:
    """Returns a dataframe as below, but with every contribution"""
    beginning_of_time = datetime.now() - timedelta(weeks=52 * 20)
    records = await get_contributions_for_guild(
        guild_id=None, user_discord_id=None, after_date=beginning_of_time.isoformat()
    )

    # convert records from json to df
    df_rows = []
    df_index = []

    logger.info("constructing dataframe for all contributions")

    if not records:
        logger.info("No contributions reported")
        return None

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
            "guilds",
            "date_of_engagement",
            "date_of_submission",
        ]
    ]

    df["activity_type"] = df.apply(lambda x: x["activity_type"]["name"], axis=1)
    df["discord_id"] = df.apply(lambda x: get_user_discord_id(x), axis=1)
    df["user"] = df.apply(lambda x: x["user"]["display_name"], axis=1)
    df["status"] = df.apply(lambda x: x["status"]["name"], axis=1)
    df["guilds"] = df.apply(lambda x: get_guild_name(x), axis=1)

    # rename columns
    df = df.rename(
        columns={
            "activity_type": "Engagement",
            "details": "Description",
            "status": "Status",
            "user": "User",
            "guild": "Guild Name",
            "discord_id": "Discord_ID",
            "date_of_submission": "Date of Submission",
            "date_of_engagement": "Date of Engagement",
        }
    )

    # sort by descending date of engagement
    df = df.sort_values(by=["Date of Engagement"], ascending=False)

    logger.info("done constructing dataframe for all contributions")

    return df


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

    if not records:
        logger.info(f"No contributions reported for {guild_id}")
        return None

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
    df["discord_id"] = df.apply(lambda x: get_user_discord_id(x), axis=1)
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


def get_user_discord_id(record):
    discord_users = record["user"]["discord_users"]
    if len(discord_users) == 0:
        return "NO_DISCORD_ID"
    return discord_users[0]["discord_id"]


def get_guild_name(record):
    guilds = record["guilds"]
    if len(guilds) == 0:
        return "NO_GUILD"
    return guilds[0]["guild"]["name"]


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
