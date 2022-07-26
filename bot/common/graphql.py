import logging

from bot import constants
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError

from bot.exceptions import (
    UserWithAddressAlreadyExists,
    UserWithTwitterHandleAlreadyExists,
)

logger = logging.getLogger(__name__)


def get_async_transport(url):
    return AIOHTTPTransport(
        url=url, headers={"Authorization": constants.Bot.protocol_token}
    )


async def execute_query(query, values):
    transport = get_async_transport(constants.Bot.protocol_url)
    try:
        async with Client(
            transport=transport, fetch_schema_from_transport=False, execute_timeout=30
        ) as session:
            query = gql(query)
            resp = await session.execute(query, variable_values=values)
            return resp
    except Exception:
        logger.exception(f"Failed to execute query {query} {values}")
        raise


async def fetch_user_by_discord_id(discord_id):
    query = """
fragment UserFragment on User {
  address
  chain_type {
    id
    name
    createdAt
    updatedAt
  }
  createdAt
  display_name
  full_name
  id
  name
  updatedAt
  guild_users {
    id
    guild_id
  }
  twitter_user {
    id
    username
  }
}

query getUser($where: UserWhereInput!,) {
    result: users(
        where: $where,
    ) {
      ...UserFragment
    }
}
    """
    result = await execute_query(
        query,
        {
            "where": {
                "discord_users": {"some": {"discord_id": {"equals": str(discord_id)}}}
            }
        },
    )
    if result:
        res = result.get("result")
        print("Fetch")
        print(result)
        print(discord_id)
        if len(res):
            return res[0]
        return None
    return result


async def get_contributions_for_guild(guild_id, user_discord_id, after_date):
    query = """
fragment ContributionFragment on Contribution {
  activity_type {
    active
    createdAt
    id
    name
    updatedAt
  }
  date_of_engagement
  date_of_submission
  details
  guilds {
    guild_id
    guild {
        discord_id
        name
    }
    id
  }
  id
  name
  proof
  status {
    createdAt
    id
    name
    updatedAt
  }
  updatedAt
  user {
    address
    createdAt
    display_name
    discord_users {
        discord_id
    }
    full_name
    id
    name
    updatedAt
  }
}

query listContributions($where: ContributionWhereInput! = {},
                        $skip: Int! = 0,
                        $orderBy: [ContributionOrderByWithRelationInput!]) {
    result: contributions(
        where: $where,
        skip: $skip,
        orderBy: $orderBy,
    ) {
      ...ContributionFragment
    }
}

    """
    guild_clause = {
        "guilds": {"some": {"guild_id": {"equals": guild_id}}},
    }
    date_clause = {"date_of_submission": {"gt": after_date}}
    user_clause = {
        "user": {
            "is": {
                "discord_users": {
                    "some": {"discord_id": {"equals": f"{user_discord_id}"}}
                }
            }
        }
    }

    clauses = []
    data = {}
    if guild_id is not None:
        clauses.append(guild_clause)
    if after_date is not None:
        clauses.append(date_clause)
    if user_discord_id is not None:
        clauses.append(user_clause)

    data = {"where": clauses[0]}
    if len(clauses) > 1:
        data = {"where": {"AND": clauses}}

    result = await execute_query(
        query,
        data,
    )
    if result:
        res = result.get("result")
        if len(res):
            return res
    return None


async def get_guild_by_discord_id(id):
    query = """
fragment GuildFragment on Guild {
  congrats_channel
  createdAt
  discord_id
  id
  logo
  name
  updatedAt
}

query getGuild($where: GuildWhereUniqueInput!) {
    result: guild(
        where: $where,
    ) {
      ...GuildFragment
    }
}
    """
    result = await execute_query(query, {"where": {"discord_id": str(id)}})
    print("Get guild")
    print(result)
    if result:
        return result.get("result")
    return result


async def get_guild_by_id(id):
    query = """
fragment GuildFragment on Guild {
  congrats_channel
  createdAt
  discord_id
  id
  logo
  name
  updatedAt
}

query getGuild($where: GuildWhereUniqueInput!) {
    result: guild(
        where: $where,
    ) {
      ...GuildFragment
    }
}
    """
    result = await execute_query(query, {"where": {"id": id}})
    print("Get guild")
    print(result)
    if result:
        return result.get("result")
    return result


async def get_guilds():
    query = """
fragment GuildFragment on Guild {
  congrats_channel
  createdAt
  discord_id
  id
  logo
  name
  updatedAt
}

query listGuilds(
  $where: GuildWhereInput! = {}
  $skip: Int! = 0
  $orderBy: [GuildOrderByWithRelationInput!]
) {
  result: guilds(where: $where, skip: $skip, orderBy: $orderBy) {
    ...GuildFragment
  }
}
    """
    result = await execute_query(query, None)
    print("list guilds")
    print(result)
    if result:
        return result.get("result")
    return result


async def create_guild_user(user_id: str, guild_db_id: str):
    query = """
mutation createGuildUser($data: GuildUserCreateInput!) {
  createGuildUser(data: $data) {
    guild_id
    user_id
  }
}
    """
    result = await execute_query(
        query,
        {
            "data": {
                "guild": {"connect": {"id": guild_db_id}},
                "user": {"connect": {"id": user_id}},
            }
        },
    )
    if result:
        return result.get("createGuildUser")
    return result


async def create_guild(guild_id):
    query = """
mutation createGuild($data: GuildCreateInput!) {
  createGuild(data: $data) {
    id
    discord_id
  }
}
    """
    result = await execute_query(
        query,
        {
            "data": {
                "discord_id": str(guild_id),
            }
        },
    )
    if result:
        return result.get("createGuild")
    return result


async def create_user(discord_id, wallet):
    query = """
mutation createUser($data: UserCreateInput!) {
  createUser(data: $data) {
    id
  }
}
    """
    data = {
        "data": {
            "address": wallet,
            "chain_type": {"connect": {"name": "ETH"}},
            "discord_users": {
                "connectOrCreate": [
                    {
                        "create": {"discord_id": str(discord_id)},
                        "where": {"discord_id": str(discord_id)},
                    }
                ]
            },
        }
    }
    result = None
    try:
        result = await execute_query(
            query,
            data,
        )
    except TransportQueryError as e:
        if is_unique_constraint_failure(e):
            err = (
                f"A user with wallet address {wallet} already exists! "
                "Please use a different wallet address to setup your "
                "profile."
            )
            raise UserWithAddressAlreadyExists(err)

    if result:
        print(result)
        return result.get("createUser")
    return result


# have a different update query for each field
#
# display name
# twitter
# discourse
async def update_user(data, where):
    query = """
fragment UserFragment on User {
  address
  chain_type {
    id
    name
    createdAt
    updatedAt
  }
  createdAt
  display_name
  full_name
  id
  name
  updatedAt
  guild_users {
    id
    guild_id
  }
}


mutation updateUser($data: UserUpdateInput!, $where: UserWhereUniqueInput!) {
  updateUser(data: $data, where: $where) {
    ...UserFragment
  }
}
    """
    result = await execute_query(
        query,
        {"data": data, "where": where},
    )
    if result:
        print(result)
        return result.get("updateUser")
    return result


async def update_user_display_name(display_name, id):
    return await update_user(
        {
            "display_name": {"set": display_name},
            "name": {"set": display_name}
        },
        {"id": id}
    )


async def update_user_twitter_handle(twitter_handle, id):
    try:
        return await update_user(
            {
                "twitter_user": {
                    "create": {
                        "username": twitter_handle,
                        "name": twitter_handle
                    }
                }
            },
            {"id": id}
        )
    except TransportQueryError as e:
        if is_unique_constraint_failure(e):
            err = (
                f"A user with twitter username {twitter_handle} already exists! "
                "Please use a different twitter account to setup your profile."
            )
            raise UserWithTwitterHandleAlreadyExists(err)


async def update_user_wallet(wallet, id):
    return await update_user({"address": {"set": wallet}}, {"id": id})


async def update_guild_name(guild_discord_id, guild_name):
    query = """
mutation updateGuild($data: GuildUpdateInput!, $where: GuildWhereUniqueInput!) {
  updateGuild(data: $data, where: $where) {
    id
  }
}
"""
    result = await execute_query(
        query,
        {
            "data": {"name": {"set": str(guild_name)}},
            "where": {"discord_id": str(guild_discord_id)},
        },
    )
    if result:
        print(result)
        return result.get("updateGuild")
    return result


def is_unique_constraint_failure(err: TransportQueryError):
    return "Unique constraint failed" in err.errors[0]["message"]
