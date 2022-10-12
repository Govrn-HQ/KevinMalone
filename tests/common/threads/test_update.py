import pytest

from bot.common.threads.update import (
    UpdateProfileFieldEmojiStep,
    UserUpdateFieldSelectStep,
    UpdateFieldStep,
)
from bot.config import get_list_of_emojis
from tests.test_utils import (
    assert_cache_metadata_content,
    assert_field_in_sent_embeds,
    assert_message_content,
    mock_gql_query,
)
from bot.common.threads.thread_builder import (
    StepKeys,
    get_cache_metadata,
    build_cache_value,
    write_cache_metadata,
)


@pytest.mark.asyncio
async def test_user_update_field_selection(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    mock_user = {
        "twitter_user": {"username": "test_twitter_user"},
        "display_name": "test_display_name",
        "address": "0x0",
    }
    step = UserUpdateFieldSelectStep(None)
    expected_emojis = get_list_of_emojis(3)
    try:
        mock_gql_query(mocker, "get_user_by_discord_id", None)
        await step.send(None, None)
        assert False
    except Exception as e:
        assert "No user for updating field" == f"{e}"

    mock_gql_query(mocker, "get_user_by_discord_id", mock_user)
    (sent_message, metadata) = await step.send(message, user_id)
    mock_channel = message.channel

    assert_field_in_sent_embeds(mock_channel, f"Display Name {expected_emojis[0]}")
    assert_field_in_sent_embeds(mock_channel, f"Twitter Handle {expected_emojis[1]}")
    assert_field_in_sent_embeds(
        mock_channel, f"Ethereum Wallet Address {expected_emojis[2]}"
    )

    assert len(metadata.keys()) == 3


@pytest.mark.asyncio
async def test_update_profile_field(mocker, thread_dependencies):
    class MockEmoji:
        def __init__(self, name):
            self.name = name

    class MockReaction:
        def __init__(self, user_id, reaction):
            self.user_id = user_id
            self.emoji = MockEmoji(reaction)

    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    step = UpdateProfileFieldEmojiStep(cache)
    emojis = get_list_of_emojis(3)
    metadata = {
        emojis[0]: "display_name",
        emojis[1]: "twitter",
        emojis[2]: "wallet",
    }
    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    for key in metadata:
        await write_cache_metadata(user_id, cache, key, metadata[key])

    raw_reaction = MockReaction(user_id, emojis[0])
    step_name, skip = await step.handle_emoji(raw_reaction)
    assert step_name is None
    assert skip is None
    assert_cache_metadata_content(user_id, cache, "field", "display_name")

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    for key in metadata:
        await write_cache_metadata(user_id, cache, key, metadata[key])

    raw_reaction = MockReaction(user_id, emojis[1])
    step_name, skip = await step.handle_emoji(raw_reaction)
    assert step_name is None
    assert skip is None
    assert_cache_metadata_content(user_id, cache, "field", "twitter")

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    for key in metadata:
        await write_cache_metadata(user_id, cache, key, metadata[key])

    raw_reaction = MockReaction(user_id, emojis[2])
    step_name, skip = await step.handle_emoji(raw_reaction)
    assert step_name is None
    assert skip is None
    assert_cache_metadata_content(user_id, cache, "field", "wallet")


@pytest.mark.asyncio
async def test_update_field_step(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    step = UpdateFieldStep(cache)
    (sent_message, metadata) = await step.send(message, "1234")
    assert_message_content(sent_message, UpdateFieldStep.update_prompt)


@pytest.mark.asyncio
async def test_update_field_step_save(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    step = UpdateFieldStep(cache)
    user_id = "1234"
    guild_id = "12345"
    mock_user = {"id": "01"}

    mock_gql_query(mocker, "get_user_by_discord_id", mock_user)
    mocked_display = mock_gql_query(mocker, "update_user_display_name", mock_user)
    mocked_twitter = mock_gql_query(mocker, "update_user_twitter_handle", mock_user)
    mocked_wallet = mock_gql_query(mocker, "update_user_wallet", mock_user)

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    await write_cache_metadata(user_id, cache, "field", "display_name")
    message.content = "test_display_name"
    await step.save(message, guild_id, user_id)
    mocked_display.assert_called_once_with(mock_user["id"], message.content)

    await write_cache_metadata(user_id, cache, "field", "twitter")
    message.content = "test_twitter"
    await step.save(message, guild_id, user_id)
    mocked_twitter.assert_called_once_with(mock_user["id"], message.content)

    await write_cache_metadata(user_id, cache, "field", "wallet")
    message.content = "test_wallet"
    await step.save(message, guild_id, user_id)
    mocked_wallet.assert_called_once_with(mock_user["id"], message.content)
