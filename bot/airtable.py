# imports
import pandas as pd
from pyairtable import Api, Base, Table
from pyairtable.formulas import match

def find_user(user_id, guild_id):

    """Return airtable record number in users table given user_id and guild_id."""

    table = Table(airtable_key, airtable_base, 'Christine Users')
    records = table.all(formula=match({'discord_id': user_id, 'guild_id': guild_id}))
    if len(records) == 1:
        record_id = records[0].get('id')
    else:
        record_id = ''
    return(record_id)

def find_discord(user_id):

    """Return airtable record number in global table given user_id."""

    table = Table(airtable_key, airtable_base, 'Christine Global')
    records = table.all(formula=match({'discord_id': user_id}))
    if len(records) == 1:
        record_id = records[0].get('id')
    else:
        record_id = ''
    return(record_id)

def find_guild(guild_id):

    """Return airtable record number in guild table given guild_id."""

    table = Table(airtable_key, airtable_base, 'Christine Guilds')
    records = table.all(formula=match({'guild_id': guild_id}))
    if len(records) == 1:
        record_id = records[0].get('id')
    else:
        record_id = ''
    return(record_id)

def update_user(record_id, id_field, id_val):

    """Add or update user ID info given ID field, value, and user table airtable record number."""

    table = Table(airtable_key, airtable_base, 'Christine Users')
    table.update(record_id, {id_field: id_val})

def create_user(user_id, guild_id):

    """Create and return new airtable record number in users table given user_id and guild_id combo.
    If user table record for said combo already exists, return existing record_id. """

    global_table = Table(airtable_key, airtable_base, 'Christine Global')
    user_table = Table(airtable_key, airtable_base, 'Christine Users')
    guild_table = Table(airtable_key, airtable_base, 'Christine Guilds')

    record_id = find_user(user_id, guild_id)

    # check if user, guild combo already exists
    if record_id != '': # existing combo
        return(record_id)
    else:  # new combo
        discord_record = find_discord(user_id)
        guild_record = find_guild(guild_id)
        # add discord id to global table if user completely new
        if discord_record == '':
            global_table.create({'discord_id': user_id})
            discord_record = find_discord(user_id)
        # create new user, guild combo record in users table
        user_table.create({'discord_id': [discord_record], 'guild_id': [guild_record]})
        record_id = find_user(user_id, guild_id)
        return(record_id)
