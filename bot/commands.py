import logging
import discord

from airtable import find_user, create_user
from cache import get_thread, build_cache_value, StepKeys, ThreadKeys, Onboarding
from config import read_file, GUILD_IDS, INFO_EMBED_COLOR, Redis
from exceptions import NotGuildException
from exceptions import ErrorHandler

logger = logging.getLogger(__name__)

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)


@bot.slash_command(
    guild_id=GUILD_IDS, description="Send users link to report engagement"
)
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


@bot.slash_command(guild_id=GUILD_IDS, description="Get started with Govern")
async def join(ctx):
    is_guild = bool(ctx.guild)
    if not is_guild:
        raise NotGuildException("Command was executed outside of a guild")

    is_user = await find_user(ctx.author.id, ctx.guild.id)
    print(is_user)
    if is_user:
        # Send welcome message and
        # And ask what journey they are
        # on by sending all the commands
        application_commands = bot.application_commands
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR, title="Welcome Back", description=f"",
        )
        for cmd in application_commands:
            if isinstance(cmd, discord.SlashCommand):
                embed.add_field(
                    name=f"/ {cmd.name}", value=cmd.description, inline=False
                )
        await ctx.response.send_message(embed=embed, ephemeral=True)
        ctx.response.is_done()
        return

    # store guild_id and disord_id
    print(ctx.guild.id)
    print(ctx.author.id)
    await create_user(ctx.author.id, ctx.guild.id)
    # check if user can be DMed
    can_send_message = ctx.can_send(discord.Message)
    if not can_send_message:
        await ctx.response.send_message(
            "I cannot onboard you. Please turn on DM's from this server!"
        )
        ctx.response.is_done()
        return

    # Get guild

    # Send messsage explaining we need to get some
    # Add a bunch of fields inline
    embed = discord.Embed(
        colour=INFO_EMBED_COLOR,
        title="Welcome",
        description=f"Thank you for joining the Govrn ecosystem! To help automate  gathering your contributions to {ctx.guild.name} we need you to provide some information. Any of the following data requests can be skipped with the ⏭️  emoji!",
    )
    # Add user to the internal cache with with appropriate stage type
    # Thread Type, thread type will have a numer of steps,
    # key:user -> value: thread_type+step
    logger.info(
        f"Key: {build_cache_value(ThreadKeys.ONBOARDING.value, '', ctx.guild.id)}"
    )
    message = await ctx.author.send(embed=embed)
    await Onboarding(
        ctx.author.id, StepKeys.USER_DISPLAY_CONFIRM.value, message.id, ctx.guild.id
    ).send(message)
    await ctx.response.send_message(
        "Check your Dms to continue onboarding", ephemeral=True
    )
    ctx.response.is_done()


# @bot.slash_command(
#     guild_id=GUILD_IDS, description="Update your profile for a given Dao"
# )
# async def update(ctx):
#     is_guild = bool(ctx.guild)
#     # If sent from guild see if user has onboarded
#     # If user has onboarded show them their profile and tell them how to update with reactions
#     #
#     # If DM show user a bunch of guilds they are in and they can choose which to update
#     # by selecting an emoji
#     #
#     # After updating a field send a thank you


# Event listners
@bot.event
async def on_application_command_error(ctx, exception):
    # All commands will be slash commands
    # Commands will be sent back from where they come from
    err = ErrorHandler(exception)
    logger.info(f"Command error type {type(exception)}")
    await ctx.response.send_message(err.msg)
    ctx.response.is_done()


@bot.event
async def on_message(message):
    print("Message")
    if message.author.bot is True:
        return

    print("Is DM")
    # Check channel DM channel
    if not isinstance(message.channel, discord.DMChannel):
        return

    print("Getting thread key")
    # Check if user has open thread
    thread_key = await Redis.get(message.author.id)
    if not thread_key:
        # TODO: It may make sense to send some sort of message here
        return

    thread = get_thread(message.author.id, thread_key)
    print(thread)
    await thread.send(message)

    print(message)
    print(message.author)


@bot.event
async def on_raw_reaction_add(payload):
    from commands import bot

    reaction = payload
    user = await bot.fetch_user(int(payload.user_id))
    channel = await bot.fetch_channel(int(reaction.channel_id))
    if user.bot is True:
        return

    print("first line")
    print(payload)
    print(reaction)
    print(user)
    print(channel)
    print(reaction.channel_id)
    # Check channel DM channel
    if not isinstance(channel, discord.DMChannel):
        return

    # Check if user has open thread
    thread_key = await Redis.get(user.id)
    if not thread_key:
        # TODO: It may make sense to send some sort of message here
        return

    thread = get_thread(user.id, thread_key)
    await thread.handle_reaction(reaction, user)

    print(reaction)
    print("hi")


bot.on_application_command_error = on_application_command_error
