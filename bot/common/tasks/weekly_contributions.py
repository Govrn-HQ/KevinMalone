import os
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta, FR
import pytz
import warnings
warnings.filterwarnings("ignore")
from pyairtable import Api, Base, Table
from pyairtable.formulas import match

# credentials
airtable_key = 'XXXX'

# global variables
govrn_base = 'XXXX'

guilds = ['MGD', 'Ludium', 'Govrn', 'DreamDAO', 'Education DAO', 'Boys Club', "Rolf's Server"]
active_guilds = ['MGD', 'Govrn', 'Education DAO', 'Boys Club', "Rolf's Server"]

# helper functions

def find_guild(guild_name):
    """Returns the community's guild ID (str) given the guild name (str)."""
    
    table = Table(airtable_key, govrn_base, "Guilds")
    records = table.all(formula=match({"guild_name": guild_name}))
    guild_id = records[0].get('fields').get('guild_id')
    
    return(guild_id)
 
def map_activity(airtable_record):
    """Given the airtable record for `ActivityType` in Activity History Staging table, returns `activity_name_only` in Activity Types table."""
    
    table = Table(airtable_key, govrn_base, "Activity Types")
    record = table.get(airtable_record)
    activity = record.get('fields').get('activity_name_only')
    
    return(activity)
  
def map_name(airtable_record):
    """Given the airtable record for `Member` in Activity History Staging table, returns `Name` in Members table."""
    
    table = Table(airtable_key, govrn_base, "Members")
    record = table.get(airtable_record)
    name = record.get('fields').get('Name')
    
    return(name)
  
def map_discord(airtable_record):
    """Given the airtable record for `member_globalID` in Activity History Staging table, returns `discord_id` in global table."""
    
    user_table = Table(airtable_key, govrn_base, "Users")
    linked_record = user_table.get(airtable_record).get('fields').get('discord_id')
    
    global_table = Table(airtable_key, govrn_base, "global")
    discord_record = global_table.get(linked_record[0])

    discord_id = discord_record.get('fields').get('discord_id')
    discord_id = int(discord_id)
    #print(type('discord_id'))
    
    return(discord_id)
  
def create_csv(guild_name):
    """Returns the community's weekly csv given the guild name."""
    
    # translate guild name to guild id
    guild_id = find_guild(guild_name)
    
    # filter Activity History Staging by guild id
    table = Table(airtable_key, govrn_base, "Activity History Staging")
    # records = table.all(formula=match({"Guild": guild_id}))
    records = table.all(formula=match({"reportedToGuild": guild_id}))
    
    # convert records from json to df
    df_rows = []
    df_index = []
    
    for rec in records: # this part can be optimized for speed later
        df_rows.append(rec['fields'])
        df_index.append(rec['id'])
    df = pd.DataFrame(df_rows, index = df_index)
    #print(df)
    
    df = df[['ActivityType', 'Description', 'status', 'Member', 'member_globalID', 'DateOfEngagement', 'DateofSubmission']]

    
    # map linked records
    df['ActivityType'] = df.apply(lambda x: map_activity(x['ActivityType'][0]), axis=1)
    df['Member'] = df.apply(lambda x: map_name(x['Member'][0]), axis=1)
    df['member_globalID'] = df.apply(lambda x: map_discord(x['member_globalID'][0]), axis=1)
    
    # rename columns
    df = df.rename(columns={"ActivityType": "Engagement", "status": "Status", "Member": "User", "member_globalID": "Discord_ID", "DateofSubmission": "Date of Submission", "DateOfEngagement": "Date of Engagement"})
    
    # sort by descending date of engagement
    df = df.sort_values(by=['Date of Engagement'], ascending=False)
    
    # drop airtable record index
    #df = df.reset_index(drop=True)
    
    return(df)

def generate_report(): 
    for guild in active_guilds:
        print(guild)
        
        # generate dataframe
        df = create_csv(guild)
        
        # convert to csv
        date = datetime.today()
        date_reformat = str(date.year)[-2:] + '_' + str(date.month).zfill(2) + '_' + str(date.day).zfill(2)
        csv_name = '{}_{}.csv'.format(guild, date_reformat)
        df.to_csv(csv_name, index=False)