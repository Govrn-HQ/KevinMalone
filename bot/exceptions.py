from discord.ext import commands


class NotGuildException(commands.CheckFailure):
    pass


class ErrorHandler:
    def __init__(self, error):
        self.err = error
        self.message = self._handle_error()

    def _handle_error(self):
        if isinstance(self.err, ErrorHandler):
            return "Please run this command in a guild!"
