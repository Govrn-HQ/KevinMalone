import discord
import json

from common.airtable import find_user, update_user, get_user_record
from config import (
    Redis,
    INFO_EMBED_COLOR,
    get_list_of_emojis,
)
from common.threads.thread_builder import (
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
    BaseThread,
    build_cache_value,
)
from common.core import bot


class UpdateProfile(BaseThread):
    name = ThreadKeys.UPDATE_PROFILE.value

    @property
    def steps(self):
        steps = (
            Step(current=SelectGuildEmojiStep(cls=self))
            .add_next_step(UserUpdateFieldSelectStep(cls=self))
            .add_next_step(UpdateProfileFieldEmojiStep(cls=self))
            .add_next_step(UpdateFieldStep())
            .add_next_step(CongratsFieldUpdateStep())
        )
        return steps.build()


class SelectGuildEmojiStep(BaseStep):
    name = StepKeys.SELECT_GUILD_EMOJI.value
    emoji = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def handle_emoji(self, raw_reaction):
        # Get reaction that has two
        # Then save the key with the guild id
        channel = await bot.fetch_channel(raw_reaction.channel_id)
        message = await channel.fetch_message(raw_reaction.message_id)
        key_vals = await Redis.get(raw_reaction.user_id)
        if not key_vals:
            return None, None
        daos = json.loads(key_vals).get("metadata").get("daos")
        selected_guild_reaction = None
        for reaction in message.reactions:
            if reaction.count >= 2:
                selected_guild_reaction = reaction
                self.cls.guild_id = daos.get(reaction.emoji)
                break
        if not selected_guild_reaction:
            raise Exception("Reacted with the wrong emoji")
        return None, None


# Next step send another message with the current profile
# and the following reactions to update a field
class UserUpdateFieldSelectStep(BaseStep):
    name = StepKeys.USER_UPDATE_FIELD_SELECT.value

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    async def send(self, message, user_id):
        fields = await get_user_record(user_id, self.cls.guild_id)
        user = fields.get("fields")
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
    name = StepKeys.CONGRATS_UPDATE_FIELD.value

    async def send(self, message, user_id):
        channel = message.channel
        sent_message = await channel.send("Thank you! Your profile has been updated")
        return sent_message, None
