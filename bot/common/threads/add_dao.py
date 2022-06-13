import logging

from bot.common.threads.onboarding import Onboarding

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
    get_user_record,
    update_guild,
)
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


class CheckDaoExists(BaseStep):
    """Step that 1. checks if the user supplied DAO ID already exists on the backend
    2. Creates the dao record 3. Directs user to the /join flow after."""
    name = StepKeys.ADD_DAO_CHECK_EXISTS

    def __init__(self, parent_thread, cache):
        self.parent_thread = parent_thread
        self.cache = cache

    async def send(self, message, user_id):
        message_content = message.content.strip()
        dao_id = None

        try:
            # we consider this exceptional if the supplied value is not
            # an actual number, but airtable will not accept values other
            # than strings for this column value
            dao_id = str(int(message_content))
        except ValueError:
            message = f"{message_content} is not a valid discord id!"
            raise ThreadTerminatingException()

        return None, {"guild_id": dao_id}

    async def control_hook(self, message, user_id):
        dao_id = str(int(message.content.strip()))
        self.parent_thread.guild_id = dao_id
        guild = await get_guild_by_guild_id(dao_id)
        if guild:
            # Check if user is a member
            user = get_user_record(user_id, dao_id)

            if user:
                message = (
                    f"It looks like guild {dao_id} has already been added as "
                    f"{guild.get('fields').get('guild_name')}, and it looks like "
                    "you're already a member! You can report your contributions "
                    "with /report!"
                )
                raise ThreadTerminatingException(message)

            # guild exists, user does not, drop into /join flow
            # TODO: How to run /join thread immediately?
            # return StepKeys.CHECK_FOR_GOVRN_PROFILE
        else:
            await create_guild(dao_id)
            # Prompt for guild name
            return StepKeys.ADD_DAO_PROMPT_NAME


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
