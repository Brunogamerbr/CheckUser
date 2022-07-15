import typing as t
import os
import asyncio


class ClientProtocol(asyncio.Protocol):
    def __init__(self, on_con_lost: asyncio.Future) -> None:
        self.on_con_lost = on_con_lost
        self.buffer = b''

    def connection_made(self, transport: asyncio.Transport) -> None:
        transport.write(b'status\n')

    def data_received(self, data: bytes) -> None:
        self.buffer += data

        if b'\r\nEND\r\n' in data:
            self.on_con_lost.set_result(True)


class ClientKillProtocol(asyncio.Protocol):
    def __init__(self, username: str, on_con_lost: asyncio.Future) -> None:
        self.username = username
        self.on_con_lost = on_con_lost

    def connection_made(self, transport: asyncio.Transport) -> None:
        transport.write(b'kill {}\n'.format(self.username.encode()))
        self.on_con_lost.set_result(True)


class OpenVPNManager:
    def __init__(self, port: int = 7505):
        self.port = port
        self.config_path = '/etc/openvpn/'
        self.config_file = 'server.conf'

    @staticmethod
    async def openvpn_is_running() -> bool:
        status = OpenVPNManager.openvpn_is_installed()

        if status:
            command = 'service openvpn status'
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if stderr.decode():
                return False

            data = stdout.decode().strip()
            status = data.find('Active: active') > -1

        return status

    @staticmethod
    def openvpn_is_installed() -> bool:
        return os.path.exists('/etc/openvpn/') and os.path.exists('/etc/openvpn/server.conf')

    @property
    def config(self) -> str:
        return os.path.join(self.config_path, self.config_file)

    async def start_manager(self) -> None:
        if os.path.exists(self.config):
            with open(self.config, 'r') as f:
                data = f.readlines()

                management = 'management localhost %d\n' % self.port
                if management in data:
                    return

                data.insert(1, management)

            with open(self.config, 'w') as f:
                f.writelines(data)

            command = 'service openvpn restart'
            await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def count_connections(self, username: str) -> int:
        loop = asyncio.get_event_loop()

        on_con_lost = loop.create_future()
        transport, protocol = await loop.create_connection(
            lambda: ClientProtocol(on_con_lost),
            'localhost',
            self.port,
        )

        await on_con_lost
        transport.close()

        data = protocol.buffer
        count = data.count(username.encode())

        return count // 2 if count > 0 else 0

    async def kill_connection(self, username: str) -> None:
        loop = asyncio.get_event_loop()

        on_con_lost = loop.create_future()
        transport, protocol = await loop.create_connection(
            lambda: ClientKillProtocol(username, on_con_lost),
            'localhost',
            self.port,
        )

        await on_con_lost
        transport.close()

    @staticmethod
    async def get_all_users() -> t.List[str]:
        command = 'cat /etc/passwd'
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        return (
            [
                line.split(':')[0]
                for line in stdout.decode().splitlines()
                if int(line.split(':')[2]) >= 1000
            ]
            if not stderr.decode()
            else []
        )

    async def count_all_connections(self) -> int:
        list_of_users = await self.get_all_users()
        return sum([await self.count_connections(username) for username in list_of_users])
