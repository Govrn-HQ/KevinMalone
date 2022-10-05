import pytest

from bot.common.threads.thread_builder import (
    StepKeys,
    get_cache_metadata,
    build_cache_value,
    write_cache_metadata,
)
from bot.common.threads.add_dao import (
    AddDaoPromptIdStep,
    AddDaoGetOrCreate,
    AddDaoPromptName,
)
from bot.exceptions import ThreadTerminatingException
from tests.test_utils import MockMessage, assert_message_content, mock_gql_query
from tests.test_utils import assert_dicts_equal, assert_cache_metadata_content


class MockThread:
    def __init__(self):
        self.guild_id = None


@pytest.mark.asyncio
async def test_add_dao_prompt_id(mocker, thread_dependencies):
    (cache, context, message, bot) = thread_dependencies
    user_id = "1234"
    step = AddDaoPromptIdStep()
    (sent_message, metadata) = await step.send(message, user_id)
    assert sent_message


@pytest.mark.asyncio
async def test_add_dao_get_or_create_send_fails(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    message.content = "this is not a valid discord id"
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    try:
        (sent_message, metadata) = await step.send(message, user_id)
        assert False
    except ThreadTerminatingException:
        # happy
        pass


@pytest.mark.asyncio
async def test_add_dao_get_or_create_send(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    dao_id = "956271220951765001"
    expected_metadata = {"guild_id": dao_id}

    message.content = dao_id
    (sent_message, metadata) = await step.send(message, user_id)
    assert sent_message is None
    assert_dicts_equal(expected_metadata, metadata)


@pytest.mark.asyncio
async def test_add_dao_get_or_create_hook_previously_added(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    guild_name = "test guild"
    dao_id = "956271220951765001"

    message.content = dao_id
    user = {"guild_users": [{"guild_id": "1"}]}
    guild = {"id": "1", "name": guild_name}
    mock_gql_query(mocker, "get_guild_by_discord_id", guild)
    mock_gql_query(mocker, "get_user_by_discord_id", user)
    try:
        step = await step.control_hook(message, user_id)
        assert False
    except ThreadTerminatingException as e:
        expected_assertion_message = AddDaoGetOrCreate.previously_added_msg % (
            dao_id,
            guild_name,
        )
        assert expected_assertion_message == f"{e}"


@pytest.mark.asyncio
async def test_add_dao_get_or_create_hook_create_user(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    guild_name = "test guild"
    dao_id = "956271220951765001"

    message.content = dao_id
    user = {
        # user is not in test guild
        "guild_users": [{"guild_id": "2"}]
    }
    guild = {"id": "1", "name": guild_name}
    mock_gql_query(mocker, "get_guild_by_discord_id", guild)
    mock_gql_query(mocker, "get_user_by_discord_id", user)
    # cache entry expected from previous interaction
    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    next_step = await step.control_hook(message, user_id)
    assert next_step == StepKeys.ADD_DAO_PREVIOUSLY_ADDED_PROMPT.value
    actual_metadata = await get_cache_metadata(user_id, cache)
    assert actual_metadata["guild_id"] == dao_id
    assert actual_metadata["guild_name"] == guild_name


@pytest.mark.asyncio
async def test_add_dao_get_or_create_hook_create_dao(mocker, thread_dependencies):
    mock_thread = MockThread()
    (cache, context, message, bot) = thread_dependencies
    step = AddDaoGetOrCreate(mock_thread, cache)
    user_id = "1234"
    dao_id = "956271220951765001"

    message.content = dao_id
    user = {
        # user is not in test guild
        "guild_users": [{"guild_id": "2"}]
    }
    mock_gql_query(mocker, "get_user_by_discord_id", user)
    mock_gql_query(mocker, "get_guild_by_discord_id", None)
    create_guild = mock_gql_query(mocker, "create_guild", None)
    # cache entry expected from previous interaction
    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    next_step = await step.control_hook(message, user_id)
    assert next_step == StepKeys.ADD_DAO_PROMPT_NAME.value
    actual_metadata = await get_cache_metadata(user_id, cache)
    assert actual_metadata["guild_id"] == dao_id
    assert actual_metadata.get("guild_name") is None
    create_guild.assert_called_once_with(dao_id)


@pytest.mark.asyncio
async def test_add_dao_prompt_name_send(mocker, thread_dependencies):
    (cache, _, message, _) = thread_dependencies
    user_id = "1234"
    prompt_name_step = AddDaoPromptName(cache)
    sent_message, _ = await prompt_name_step.send(message, user_id)
    assert_message_content(sent_message, AddDaoPromptName.guild_name_prompt)


@pytest.mark.asyncio
async def test_add_dao_prompt_name_save(mocker, thread_dependencies):
    (cache, _, message, _) = thread_dependencies
    user_id = "1234"
    dao_id = "12345"
    dao_name = "test dao"
    mock_message = MockMessage()
    mock_message.content = dao_name
    await cache.set(user_id, build_cache_value("t", "s", "1", "1"))
    await write_cache_metadata(user_id, cache, "guild_id", dao_id)
    update_guild_name = mock_gql_query(mocker, "update_guild_name", None)

    prompt_name_step = AddDaoPromptName(cache)
    await prompt_name_step.save(mock_message, dao_id, user_id)

    # assert gql query called w arguments
    update_guild_name.assert_awaited_once_with(dao_id, dao_name)

    # assert cache metadata
    await assert_cache_metadata_content(user_id, cache, "guild_name", dao_name)
