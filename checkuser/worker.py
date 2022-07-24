import threading
import socket
import json
import typing as t

from . import logger
from .utils import HttpParser
from .checker import SSHChecker, OVPNChecker


class Command:
    def execute(self) -> dict:
        raise NotImplementedError('This method must be implemented')


class CheckerUser(Command):
    def __init__(self, content: str) -> None:
        if not content:
            raise ValueError('User name is required')

        self.content = content
        self.ssh_checker = SSHChecker(content)
        self.ovpn_checker = OVPNChecker(content)

    def execute(self) -> dict:
        try:
            return {
                'username': self.content,
                'count_connection': (self.ssh_checker.count_connections())
                + (self.ovpn_checker.count_connections()),
                'limit_connection': self.ssh_checker.limit_connections(),
                'expiration_date': self.ssh_checker.expiration_date(),
                'expiration_days': self.ssh_checker.expiration_days(),
            }
        except Exception as e:
            return {'error': str(e)}


class KillUser(Command):
    def __init__(self, content: str) -> None:
        if not content:
            raise ValueError('User name is required')

        self.ssh_checker = SSHChecker(content)
        self.ovpn_checker = OVPNChecker(content)

    def execute(self) -> dict:
        try:
            self.ssh_checker.stop_connections()
            self.ovpn_checker.stop_connections()
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}


class AllConnections(Command):
    def __init__(self, *_) -> None:
        pass

    def execute(self) -> dict:
        try:
            return {
                'count': (SSHChecker.count_all_connections())
                + (OVPNChecker.count_all_connections()),
                'success': True,
            }
        except Exception as e:
            return {'error': str(e)}


class CommandFactory:
    def __init__(self) -> None:
        self.commands = {
            'check': CheckerUser,
            'kill': KillUser,
            'all_connections': AllConnections,
        }

    def handle(self, command: str, content: str) -> dict:
        try:
            command_class = self.commands[command]
            command = command_class(content)

            return command.execute()
        except KeyError:
            raise ValueError('Unknown command')


class Handler(threading.Thread):
    def __init__(self, client: socket.socket, addr: t.Tuple[str, int]) -> None:
        super(Handler, self).__init__()
        self.client = client
        self.addr = addr
        self.command_handler = CommandFactory()

    def handle(self, command: str, content: str) -> None:
        try:
            response = self.command_handler.handle(command, content)
            response = json.dumps(response, indent=4)
            response = HttpParser.build_response(
                status=200,
                headers={'Content-Type': 'Application/json'},
                body=response,
            )
            self.client.send(response.encode('utf-8'))
        except Exception as e:
            response = HttpParser.build_response(
                status=500,
                headers={'Content-Type': 'Application/json'},
                body=json.dumps({'error': str(e)}, indent=4),
            )
            self.client.send(response.encode('utf-8'))

    def process(self) -> None:
        data = self.client.recv(8192)
        parser = HttpParser.of(data.decode('utf-8'))

        if not data or not parser.path:
            self.client.send(
                HttpParser.build_response(
                    status=400,
                    headers={'Content-Type': 'Application/json'},
                    body=json.dumps({'error': 'Bad request'}, indent=4),
                ).encode('utf-8')
            )
            return

        split = parser.path.split('/')
        command = split[1]
        content = split[2].split('?')[0] if len(split) > 2 else None

        self.handle(command, content)

    def run(self):
        try:
            self.process()
        except Exception as e:
            logger.exception('Error: {}'.format(e))

        self.client.close()
