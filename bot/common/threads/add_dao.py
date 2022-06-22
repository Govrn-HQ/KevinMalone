import logging

from bot.common.threads.thread_builder import (
    BaseThread,
    ThreadKeys,
    BaseStep,
    StepKeys,
    Step,
)
from bot.common.airtable import (
    get_guild_by_guild_id,
    create_guild,
    create_user,
    update_guild,
    find_user,
)
from bot.common.graphql import create_guild_user
from bot.common.threads.thread_builder import (
    write_cache_metadata,
    get_cache_metadata_key,
)
from bot.exceptions import ThreadTerminatingException


logger = logging.getLogger(__name__)


class AddDaoPromptId(BaseStep):
    """Prompts the user to input the discord ID of the guild they wish to add"""

    name = StepKeys.ADD_DAO_PROMPT_ID

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What is the discord ID of the guild you'd like to add? "
            "(You can find this by right-clicking the guild icon and clicking "
            '"Copy ID")'
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        message_content = message.content.strip()
        dao_id = None

        try:
            # we consider this exceptional if the supplied value is not
            # an actual number, but airtable will not accept values other
            # than strings for this column value
            dao_id = str(int(message_content))
        except ValueError:
            message = f"{message_content} is not a valid discord id!"
            raise ThreadTerminatingException(message)

        guild = await get_guild_by_guild_id(dao_id)
        if guild:
            message = (
                f"It looks like guild {dao_id} has already been onboarded as "
                f"{guild.get('name')}! You can report your "
                " contributions with /report!"
            )
            raise ThreadTerminatingException(message)

        # add validated dao_id to metadata cache for lookup on next step
        await write_cache_metadata(user_id, self.cache, "guild_id", dao_id)

        user = await find_user(user_id)
        id = await create_guild(user.get("id"), dao_id)
        # Create guild user
        await create_guild_user(user.get("id"), id.get("id"))


class AddDaoPromptName(BaseStep):
    """Prompts the user to input the name of the guild they wish to add"""

    name = StepKeys.ADD_DAO_PROMPT_NAME

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send(
            "What is the friendly name of the guild you'd like to add?"
        )
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        # retrieve dao_id from cache
        guild_name = message.content.strip()
        dao_id = await get_cache_metadata_key(user_id, self.cache, "guild_id")
        await update_guild(dao_id, "guild_name", guild_name)
        await write_cache_metadata(user_id, self.cache, "guild_name", guild_name)


class AddDaoSuccess(BaseStep):
    """Sends a success message for adding the Guild"""

    name = StepKeys.ADD_DAO_SUCCESS

    def __init__(self, cache):
        super().__init__()
        self.cache = cache

    async def send(self, message, user_id):
        guild_name = await get_cache_metadata_key(user_id, self.cache, "guild_name")
        return (
            await message.channel.send(
                f"Thanks for adding {guild_name} as a new guild! You can now "
                "report your contributions using the /report command."
            ),
            None,
        )


class AddDao(BaseThread):
    name = ThreadKeys.ADD_DAO.value

    async def get_steps(self):
        steps = (
            Step(current=AddDaoPromptId(self.cache))
            .add_next_step(AddDaoPromptName(self.cache))
            .add_next_step(AddDaoSuccess(self.cache))
        )

        return steps.build()
