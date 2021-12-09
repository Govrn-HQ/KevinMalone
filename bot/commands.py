import logging
import discord

from config import read_file, GUILD_IDS, INFO_EMBED_COLOR
from checks import is_guild_msg
from stubs import get_user, store_user_ids
from exceptions import NotGuildException
from exceptions import ErrorHandler

logger = logging.getLogger(__name__)

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


@bot.slash_command(guild_id=GUILD_IDS, help="Send users link to report engagement")
async def report(ctx):
    is_guild = bool(ctx.guild)
    if not is_guild:
        raise NotGuildException("Command was executed outside of a guild")

    airtableLinks = read_file()
    airtableLink = airtableLinks.get(str(ctx.guild.id))

    if airtableLink:
        await bot.fetch_user(int(ctx.author.id))
        await ctx.response.send_message(
            f"Add contributions to the following airtable {airtableLink}",
            ephemeral=True,
        )
        ctx.response.is_done()
    else:
        await ctx.response.send_message(
            "No airtable link was provided for this Discord server", ephemeral=True
        )
        ctx.response.is_done()


# Join should be pretty simple
# If the user exists in airtable
# then send a message asking about their adventure
# If they aren't a user dm
# In DM send a prompt and start asking for information
# If a user sends a random message then tell them to continue
# on the flow, if they repond with an unsupported emjoi
# do the same.
#
# Keep an internal dictionary to keep track of what thread they are on


# If not a user
# Check if bot can DM
# If false than tell user to enable dms
# If true than DM requesting information


@bot.slash_command(guild_id=GUILD_IDS, help="Get started with Govern")
async def join(ctx):
    is_guild = bool(ctx.guild)
    if not is_guild:
        raise NotGuildException("Command was executed outside of a guild")

    is_user = get_user(ctx.author)
    if is_user:
        # Send welcome message and
        # And ask what journey they are
        # on by sending all the commands
        pass
    # store guild_id and disord_id
    store_user_ids(ctx.guild, ctx.author.id)
    # check if user can be DMed
    can_send_message = ctx.can_send(discord.Message)
    if not can_send_message:
        await ctx.response.send_message(
            "I cannot onboard you. Please turn on DM's from this server!"
        )
        ctx.is_done()
        return

    # Get guild

    # Send messsage explaining we need to get some
    embed = discord.Embed(
        colour=INFO_EMBED_COLOR,
        title="Welcome",
        description=f"Thank you for joining the Govrn ecosystem! To help automate  gathering your contributions to {ctx.guild.name} we need you to provide some information. Any of the following data requests cabn be skipped with the ⏭️  emoji!",
    )
    await ctx.author.send(embed=embed, ephemeral=True)
    await ctx.response.is_done()


# Event listners
@bot.event
async def on_application_command_error(ctx, exception):
    # All commands will be slash commands
    # Commands will be sent back from where they come from
    err = ErrorHandler(exception)
    logger.info(f"Command error type {type(exception)}")
    await ctx.response.send_message(err.msg)
    ctx.response.is_done()


bot.on_application_command_error = on_application_command_error
