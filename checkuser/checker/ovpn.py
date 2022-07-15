import typing as t
import os
import asyncio


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
        try:
            reader, writer = await asyncio.open_connection(host='localhost', port=self.port)
            writer.write(b'status\n')
            await writer.drain()

            buffer = b''
            while True:
                data = await reader.read(1024)
                buffer += data

                if b'\r\nEND\r\n' in data or not data:
                    break

            writer.close()
            count = buffer.count(username.encode())
            return count // 2 if count > 0 else 0
        except:
            return 0

    async def kill_connection(self, username: str) -> None:
        try:
            _, writer = await asyncio.open_connection(host='localhost', port=self.port)
            writer.write(b'kill %s\n' % username.encode())
            await writer.drain()
            writer.close()
        except:
            pass

    @staticmethod
    async def get_all_users() -> t.List[str]:
        command = 'cat /etc/passwd'
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if stderr.decode():
            return []

        data = stdout.decode().splitlines()
        data = list(filter(lambda x: int(x.split(':')[2]) >= 1000, data))
        return [line.split(':')[0] for line in data]

    async def count_all_connections(self) -> int:
        list_of_users = await self.get_all_users()
        return sum([await self.count_connections(username) for username in list_of_users])
