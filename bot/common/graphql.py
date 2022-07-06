import logging

from bot import constants
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

logger = logging.getLogger(__name__)


def get_async_transport(url):
    return AIOHTTPTransport(
        url=url, headers={"Authorization": constants.Bot.protocol_token}
    )


async def execute_query(query, values):
    transport = get_async_transport(constants.Bot.protocol_url)
    try:
        async with Client(
            transport=transport, fetch_schema_from_transport=False
        ) as session:
            query = gql(query)
            resp = await session.execute(query, variable_values=values)
            return resp
    except Exception:
        logger.exception(f"Failed to execute query {query} {values}")
        return None


async def fetch_user(id):
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
        {"where": {"discord_users": {"some": {"discord_id": {"equals": str(id)}}}}},
    )
    if result:
        res = result.get("result")
        print("Fetch")
        print(result)
        print(id)
        if len(res):
            return res[0]
        return res
    return result


async def list_user_contributions_for_guild(user_discord_id, guild_id, after_date):
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
  attestations {
    id
  }
}

query listContributions($where: ContributionWhereInput! = {},
                        $skip: Int! = 0,
                        $first: Int! = 10,
                        $orderBy: [ContributionOrderByWithRelationInput!]) {
    result: contributions(
        where: $where,
        skip: $skip,
        take: $first,
        orderBy: $orderBy,
    ) {
      ...ContributionFragment
    }
}

    """
    result = await execute_query(
        query,
        {
            "where": {
                "AND": [
                    {"guilds": {"some": {"guild_id": {"equals": guild_id}}}},
                    {
                        "user": {
                            "is": {
                                "discord_users": {
                                    "some": {
                                        "discord_id": {"equals": f"{user_discord_id}"}
                                    }
                                }
                            }
                        }
                    },
                    {"date_of_submission": {"gt": after_date}},
                ]
            }
        },
    )
    if result:
        return result.get("result")
    return result


async def get_guild(id):
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


async def create_guild_user(user_id, guild_id):
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
                "guild": {"connect": {"id": guild_id}},
                "user": {"connect": {"id": user_id}},
            }
        },
    )
    if result:
        return result.get("createGuildUser")
    return result


async def create_guild(user_id, guild_id):
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
    result = await execute_query(
        query,
        {
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
        },
    )
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
    return await update_user({"display_name": {"set": display_name}}, {"id": id})


async def update_user_twitter_handle(twitter_handle, id):
    return await update_user(
        {"twitter_user": {"create": {"username": twitter_handle}}}, {"id": id}
    )


async def update_user_wallet(wallet, id):
    return await update_user({"address": {"set": wallet}}, {"id": id})


async def update_guild(id, val):
    query = """
mutation updateUser($data: GuildUpdateInput!, $where: GuildWhereUniqueInput!) {
  updateGuild(data: $data, where: $where) {
    id
  }
}
"""
    result = await execute_query(
        query,
        {"data": {"name": {"set": str(val)}}, "where": {"discord_id": str(id)}},
    )
    if result:
        print(result)
        return result.get("updateGuild")
    return result
