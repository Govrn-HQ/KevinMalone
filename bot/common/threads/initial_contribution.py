import discord
import hashlib
from common.airtable import (
    add_user_to_contribution,
    get_highest_contribution_records,
    get_contribution_records,
    get_user_record,
)
from common.threads.thread_builder import (
    BaseThread,
    BaseStep,
    StepKeys,
    Step,
    ThreadKeys,
)
from config import YES_EMOJI, NO_EMOJI, INFO_EMBED_COLOR


class SendContributionInstructions(BaseStep):
    """
    There is an assumption here that there will be
    at least one contribution.
    """

    name = StepKeys.SEND_CONTRIBUTION_INSTRUCTION.value

    def __init__(self, guild_id, contribution_number, instruction, total_contributions):
        self.guild_id = guild_id
        self.contribution_number = contribution_number
        self.instruction = instruction
        self.total_contributions = total_contributions
        self.no_record = False

    async def send(self, message, user_id):
        channel = message.channel
        user_record = await get_user_record(user_id, self.guild_id)
        user_dao_id = user_record.get("fields").get("user_dao_id")

        record = await get_highest_contribution_records(
            self.guild_id,
            user_dao_id,
            self.total_contributions,
        )
        if record:
            embed = discord.Embed(
                colour=INFO_EMBED_COLOR,
                description="You have already completed all of the"
                " initial contributions for this guild!"
                " To report new contributions use the `/report` command",
            )
            sent_message = await channel.send(embed=embed)
            self.no_record = True
            return message, None

        embed = discord.Embed(
            colour=INFO_EMBED_COLOR,
            description=self.instruction,
            title="Have you completed the below?",
        )
        sent_message = await channel.send(embed=embed)
        await sent_message.add_reaction(YES_EMOJI)
        await sent_message.add_reaction(NO_EMOJI)

        await add_user_to_contribution(self.guild_id, user_id, self.contribution_number)

        return sent_message, None

    async def control_hook(self, message, user_id):
        if self.no_record:
            return StepKeys.END.value


class InitialContributionConfirmEmojiStep(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_CONFIRM_EMOJI.value
    emoji = True

    @property
    def emojis(self):
        return [YES_EMOJI, NO_EMOJI]

    async def handle_emoji(self, raw_reaction):
        if raw_reaction.emoji.name in self.emojis:
            if raw_reaction.emoji.name == NO_EMOJI:
                return StepKeys.INITIAL_CONTRIBUTION_REJECT.value, None
            return StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value, None
        raise Exception("Reacted with the wrong emoji")


class InitialContributionAccept(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value
    trigger = True

    def __init__(self, contribution_number, total_steps):
        self.contribution_number = contribution_number
        self.total_steps = total_steps

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "Congratulations on completeting that contribution"
            f" and improving our community! (Step {self.contribution_number}"
            f" of {self.total_steps}) "
        )
        return message, None


class InitialContributionReject(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REJECT.value

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "No worries! When you do complete that contribution run"
            " the `/add_initial_contribution command!`"
        )
        return message, None


class InitialContributionReportCommand(BaseStep):
    name = StepKeys.INITIAL_CONTRIBUTION_REPORT_COMMAND.value

    def __init__(self, cls):
        self.cls = cls

    async def send(self, message, userid):
        channel = message.channel
        message = await channel.send(
            "In order to send add more new contributions call the `/report` command"
        )
        return message, None


class InitialContributions(BaseThread):
    name = ThreadKeys.INITIAL_CONTRIBUTIONS.value

    async def build_steps(self):
        if not self.guild_id:
            raise Exception("No provided guild_id for Initial COntribution thread")
        contribution_records = await get_contribution_records(self.guild_id)
        previous_step = None
        for i, record in enumerate(
            sorted(
                contribution_records,
                key=lambda record: record.get("fields", {"order": 1}).get("order"),
            )
        ):
            fields = record.get("fields")
            order = fields.get("order")
            instructions = fields.get("instructions")

            current_step = Step(
                current=SendContributionInstructions(
                    guild_id=self.guild_id,
                    contribution_number=order,
                    instruction=instructions,
                    total_contributions=len(contribution_records),
                ),
                hash_=hashlib.sha256(
                    f"{previous_step.hash_}{SendContributionInstructions.name}".encode()
                ).hexdigest()
                if previous_step
                else hashlib.sha256("".encode()).hexdigest(),
            )

            yes_fork = Step(
                current=InitialContributionAccept(
                    contribution_number=order, total_steps=len(contribution_records)
                )
            )
            if len(contribution_records) == i + 1:
                yes_fork.add_next_step(InitialContributionReportCommand(cls=self))
            fork_steps = [
                yes_fork,
                Step(current=InitialContributionReject()).build(),
            ]
            current_tree = (
                current_step.add_next_step(InitialContributionConfirmEmojiStep())
                .fork(fork_steps)
                .build()
            )

            if not previous_step:
                previous_step = current_tree
                previous_step = yes_fork
            else:
                # Return the yes path
                previous_step.add_next_step(current_tree)
                print(current_tree.next_steps.keys())
                print(
                    current_tree.next_steps.get(
                        StepKeys.INITIAL_CONTRIBUTION_ACCEPT.value
                    )
                )
                previous_step = yes_fork
            print(previous_step.hash_)
        if not previous_step:
            raise Exception(
                "Steps are None, most likely no contribution records were found"
            )
        return previous_step.build()

    async def get_steps(self):
        contribution_step = await self.build_steps()
        return contribution_step.build()
