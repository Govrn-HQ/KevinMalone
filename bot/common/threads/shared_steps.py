from config import (
    Redis,
    INFO_EMBED_COLOR,
    get_list_of_emojis,
)

from common.threads.thread_builder import BaseStep


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
