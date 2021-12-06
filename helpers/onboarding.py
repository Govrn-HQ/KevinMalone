"""import logging
import discord
import pyairtable
from config import read_file, GUILD_IDS
from pyairtable import Api, Base, Table
from pyairtable.formulas import match

async def chooseID(ctx):
    id_types = ["🐦", "🗝"] 
    message = await ctx.send_message("Awesome! What ID do you want to upload first?  Note that we need your IDs so we can reward you points for your assoicated conitrbution!", ephemeral=True)
    for x in id_types:
        message.add_reaction(x)
        ctx.response.is_done()
"""