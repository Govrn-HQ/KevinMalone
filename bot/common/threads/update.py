import discord
import json

from bot.common.airtable import find_user, update_user, get_user_record
from bot.config import (
    Redis,
    INFO_EMBED_COLOR,
    get_list_of_emojis,
)
from bot.common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
    BaseThread,
    build_cache_value,
)

from bot.common.threads.shared_steps import SelectGuildEmojiStep


class UpdateProfile(BaseThread):
    """A thread to update a Govrn Guild Profile

    The current steps allow the user to select a guild
    then select the field they want to update; then
    update that field with a new value; then congradulate
    them.
    """

    name = ThreadKeys.UPDATE_PROFILE.value

    async def get_steps(self):
        steps = (
            Step(current=SelectGuildEmojiStep(cls=self))
            .add_next_step(UserUpdateFieldSelectStep(cls=self))
            .add_next_step(UpdateProfileFieldEmojiStep(cls=self))
            .add_next_step(UpdateFieldStep())
            .add_next_step(CongratsFieldUpdateStep())
        )
        return steps.build()


class UserUpdateFieldSelectStep(BaseStep):
    """Sends the message with all the fields a user can select from"""

    name = StepKeys.USER_UPDATE_FIELD_SELECT.value

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def send(self, message, user_id):
        user = await get_user_record(user_id, self.cls.guild_id)
        if not user:
            raise Exception("No user for updating field")
        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description="Please select one of the following fields to update via emoji",
        )
        emojis = get_list_of_emojis(4)
        embed.add_field(
            name=f"Display Name {emojis[0]}", value=user.get("display_name")
        )
        embed.add_field(name=f"Twitter Handle {emojis[1]}", value=user.get("twitter"))
        embed.add_field(
            name=f"Ethereum Wallet Address {emojis[2]}", value=user.get("wallet")
        )
        embed.add_field(
            name=f"Discourse Handle {emojis[3]}", value=user.get("discourse")
        )

        channel = message.channel
        sent_message = await channel.send(embed=embed)
        for emoji in emojis:
            await sent_message.add_reaction(emoji)
        return (
            sent_message,
            {
                emojis[0]: "display_name",
                emojis[1]: "twitter",
                emojis[2]: "wallet",
                emojis[3]: "discourse",
            },
        )


class UpdateProfileFieldEmojiStep(BaseStep):
    """Stores the field user responds with to the cache"""

    name = StepKeys.UPDATE_PROFILE_FIELD_EMOJI.value
    emoji = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def handle_emoji(self, raw_reaction):
        key_vals = await Redis.get(raw_reaction.user_id)
        if not key_vals:
            return None, None
        values = json.loads(key_vals)
        values["metadata"] = {
            "field": values.get("metadata").get(raw_reaction.emoji.name)
        }
        await Redis.set(
            raw_reaction.user_id,
            build_cache_value(**values),
        )
        return None, None


class UpdateFieldStep(BaseStep):
    """Asks the user which field to update and then saves the response"""

    name = StepKeys.UPDATE_FIELD.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send("What value would you like to use instead")
        return sent_message, None

    async def save(self, message, guild_id, user_id):
        key_vals = await Redis.get(user_id)
        if not key_vals:
            return
        metadata = json.loads(key_vals).get("metadata")
        field = metadata.get("field")
        if not field:
            raise Exception("No field present to update")
        record_id = await find_user(user_id, guild_id)
        await update_user(record_id, field, message.content.strip())


class CongratsFieldUpdateStep(BaseStep):
    """Sends the user a congratulations message and then ends the thread"""

    name = StepKeys.CONGRATS_UPDATE_FIELD.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send("Thank you! Your profile has been updated")
        return sent_message, None
