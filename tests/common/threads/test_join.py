import pytest

from bot.common.threads.thread_builder import (
    ThreadKeys,
    StepKeys,
    get_cache_metadata,
    build_cache_value,
    write_cache_metadata,
)
from bot.common.threads.onboarding import (
    DISCORD_DISPLAY_NAME_CACHE_KEY,
    AssociateExistingUserWithGuild,
    CheckIfUserExists,
    UserDisplayConfirmationStep,
)
from bot.config import NO_EMOJI, YES_EMOJI

from tests.test_utils import (
    MockMessage,
    assert_message_content,
    assert_message_reaction,
    mock_gql_query,
)
from tests.test_utils import assert_dicts_equal, assert_cache_metadata_content


@pytest.mark.asyncio
async def test_check_if_user_exists(mocker, thread_dependencies):
    user_id = "1234"
    test_display_name = "test_display_name"
    address = "0xdeadbeef"
    mock_user = {"id": "01", "display_name": test_display_name, "address": address}
    (cache, context, message, bot) = thread_dependencies

    step = CheckIfUserExists(cache)
    (msg, metadata) = await step.send(None, None)
    assert msg is None
    assert metadata is None

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    mock_gql_query(mocker, "get_user_by_discord_id", mock_user)
    next_step_key = await step.control_hook(None, user_id)
    assert_cache_metadata_content(user_id, cache, "display_name", test_display_name)
    assert_cache_metadata_content(user_id, cache, "wallet_address", address)
    assert next_step_key == StepKeys.ASSOCIATE_EXISTING_USER_WITH_GUILD.value


@pytest.mark.asyncio
async def test_check_if_user_exists_dne(mocker, thread_dependencies):
    user_id = "1234"
    (cache, context, message, bot) = thread_dependencies

    step = CheckIfUserExists(cache)
    mock_gql_query(mocker, "get_user_by_discord_id", None)
    next_step_key = await step.control_hook(None, user_id)
    assert len(cache.internal) == 0
    assert next_step_key == StepKeys.USER_DISPLAY_CONFIRM.value


@pytest.mark.asyncio
async def test_associate_existing_user(mocker, thread_dependencies):
    user_id = "1234"
    test_display_name = "test_display_name"
    address = "0xdeadbeef"
    mock_user = {"id": "01", "display_name": test_display_name, "address": address}
    mock_guild = {"id": "1", "name": "test_guild_name"}
    guild_id = "12345"
    (cache, context, message, bot) = thread_dependencies

    step = AssociateExistingUserWithGuild(cache, guild_id)

    next_step = await step.control_hook(message, user_id)
    assert next_step == StepKeys.END.value

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))

    mock_gql_query(mocker, "get_guild_by_discord_id", mock_guild)
    await write_cache_metadata(user_id, cache, "user_db_id", mock_user["id"])
    mocked_create = mock_gql_query(mocker, "create_guild_user", None)

    await write_cache_metadata(user_id, cache, "guild_name", mock_guild["name"])
    await write_cache_metadata(
        user_id, cache, "display_name", mock_user["display_name"]
    )
    await write_cache_metadata(user_id, cache, "wallet_address", mock_user["address"])

    (sent_message, metadata) = await step.send(message, user_id)

    mocked_create.assert_called_once_with(mock_user["id"], mock_guild["id"])

    assert_message_content(
        sent_message,
        AssociateExistingUserWithGuild.associate_msg_fmt
        % (test_display_name, address, mock_guild["name"]),
    )


@pytest.mark.asyncio
async def test_user_display_confirmation(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    bot.mock_user.display_name = user_id
    step = UserDisplayConfirmationStep(cache, bot)

    emojis = step.emojis
    assert YES_EMOJI in emojis
    assert NO_EMOJI in emojis
    assert len(emojis) == 2

    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))

    (sent_message, metadata) = await step.send(message, user_id)

    assert_message_content(
        sent_message, f"{UserDisplayConfirmationStep.msg} `{user_id}`"
    )
    assert_message_reaction(sent_message, YES_EMOJI)
    assert_message_reaction(sent_message, NO_EMOJI)
    assert_cache_metadata_content(
        user_id, cache, DISCORD_DISPLAY_NAME_CACHE_KEY, user_id
    )
