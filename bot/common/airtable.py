import asyncio
from pyairtable import Table
from pyairtable.formulas import match
from config import AIRTABLE_BASE, AIRTABLE_KEY


async def find_user(user_id, guild_id):

    """Return airtable record number in users table given user_id and guild_id."""

    loop = asyncio.get_running_loop()

    def _find_user():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Users")
        records = table.all(
            formula=match({"discord_id": str(user_id), "guild_id": str(guild_id)})
        )
        if len(records) == 1:
            record_id = records[0].get("id")
        else:
            record_id = ""
        return record_id

    return await loop.run_in_executor(None, _find_user)


async def get_user_record(user_id, guild_id):

    """Return airtable record number in users table given user_id and guild_id."""

    loop = asyncio.get_running_loop()

    def _find_user():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Users")
        records = table.all(
            formula=match({"discord_id": str(user_id), "guild_id": str(guild_id)})
        )
        if len(records) == 1:
            record_id = records[0]
        else:
            record_id = None
        return record_id

    return await loop.run_in_executor(None, _find_user)


async def get_contribution_records(user_id, guild_id, order=1):

    """"""

    loop = asyncio.get_running_loop()

    def _get_contribution():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Contribution Flow")
        records = table.all(formula=match({"guild_id": str(guild_id), "order": order}))
        if len(records) == 1:
            record_id = records
        else:
            record_id = None
        return record_id

    return await loop.run_in_executor(None, _get_contribution)


# cannot use in async
def find_discord(user_id):

    """Return airtable record number in global table given user_id."""
    table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Global")
    records = table.all(formula=match({"discord_id": user_id}))
    if len(records) == 1:
        record_id = records[0].get("id")
    else:
        record_id = ""
    return record_id


async def get_discord_record(user_id):

    """Return airtable record number in global table given user_id."""
    loop = asyncio.get_running_loop()

    def _get_discord_record():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Global")
        records = table.all(formula=match({"discord_id": user_id}))
        record = None
        if len(records) == 1:
            record = records[0]
        return record

    return await loop.run_in_executor(None, _get_discord_record)


async def find_guild(guild_id):

    """Return airtable record number in guild table given guild_id."""

    loop = asyncio.get_running_loop()

    def _find_guild():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Guilds")
        records = table.all(formula=match({"guild_id": guild_id}))
        if len(records) == 1:
            record_id = records[0].get("id")
        else:
            record_id = ""
        return record_id

    return await loop.run_in_executor(None, _find_guild)


async def get_guild_by_guild_id(guild_id):

    """Return airtable record number in guild table given guild_id."""

    loop = asyncio.get_running_loop()

    def _find_guild():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Guilds")
        records = table.all(formula=match({"guild_id": guild_id}))
        if len(records) == 1:
            record_id = records[0]
        else:
            record_id = ""
        return record_id

    return await loop.run_in_executor(None, _find_guild)


async def get_guild(record_id):

    """Return airtable record number in guild table given guild_id."""

    loop = asyncio.get_running_loop()

    def _find_guild():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Guilds")
        records = table.get(str(record_id))
        record = {}
        if records:
            record = records.get("fields")
        return record

    return await loop.run_in_executor(None, _find_guild)


async def update_user(record_id, id_field, id_val):

    """Add or update user ID info given ID field, value,
    and user table airtable record number."""

    loop = asyncio.get_running_loop()

    def _update_user():
        table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Users")
        table.update(record_id, {id_field: id_val})

    return await loop.run_in_executor(None, _update_user)


async def create_user(user_id, guild_id):

    """Return new airtable record # in users table given user_id & guild_id.
    If user table record for combo already exist, return existing record_id."""

    loop = asyncio.get_running_loop()

    record_id = await find_user(user_id, guild_id)
    guild_record = await find_guild(guild_id)

    def _create_user():
        global_table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Global")
        user_table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Users")
        guild_table = Table(AIRTABLE_KEY, AIRTABLE_BASE, "Christine Guilds")

        # check if user, guild combo already exists
        if record_id != "":  # existing combo
            return record_id
        else:  # new combo
            # add discord id to global table if user completely new
            discord_record = find_discord(user_id)
            if discord_record == "":
                global_table.create({"discord_id": str(user_id)})
                discord_record = find_discord(user_id)
            user_dao_id = guild_table.get(guild_record).get("fields").get("total") + 1
            user_table.create(
                {
                    "discord_id": [discord_record],
                    "guild_id": [guild_record],
                    "user_dao_id": str(user_dao_id),
                }
            )
            return record_id

    return await loop.run_in_executor(None, _create_user)
