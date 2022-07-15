import asyncio

from checkuser.utils import logger

from ..checker import check_user, kill_user, count_all_connections
from ..utils.config import Config


class Command:
    def execute(self) -> dict:
        raise NotImplementedError('This method must be implemented')


class CheckUserCommand(Command):
    def __init__(self, content: str) -> None:
        if not content:
            raise ValueError('User name is required')

        self.content = content

    async def execute(self) -> dict:
        data = await check_user(self.content)

        for exclude in Config().exclude:
            if exclude in data:
                logger.debug(f'Exclude: {exclude}')
                del data[exclude]

        return data


class KillUserCommand(Command):
    def __init__(self, content: str) -> None:
        if not content:
            raise ValueError('User name is required')

        self.content = content

    async def execute(self) -> dict:
        return await kill_user(self.content)


class AllConnectionsCommand(Command):
    def __init__(self, *_):
        pass

    async def execute(self) -> dict:
        return await count_all_connections()


class CommandHandler:
    def __init__(self) -> None:
        self.commands = {
            'check': CheckUserCommand,
            'kill': KillUserCommand,
            'all_connections': AllConnectionsCommand,
        }

    async def handle(self, command: str, content: str) -> dict:
        try:
            command_class = self.commands[command]
            command = command_class(content)

            return await command.execute()
        except KeyError:
            raise ValueError('Unknown command')
