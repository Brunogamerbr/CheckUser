import asyncio
import datetime
import re
import os


class SSHChecker:
    def __init__(self, username: str) -> None:
        self.username = username

    async def expiration_date(self) -> str:
        cmd = 'chage -l ' + self.username
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        if stderr:
            return 'never'

        pattern = re.compile(r'Account expires\s+:\s+(.*)|Conta expira\s+:\s+(.*)')
        match = pattern.search(stdout.decode('utf-8'))
        return match.group(1) or match.group(2)

    async def expiration_days(self, date: str = None) -> int:
        if not date:
            date = await self.expiration_date()

        if date == 'never':
            return -1

        try:
            today = datetime.datetime.now()
            return (datetime.datetime.strptime(date, '%b %d, %Y') - today).days
        except ValueError:
            return -1

    async def limit_connections(self) -> int:
        file_with_limit = '/root/usuarios.db'

        if not os.path.exists(file_with_limit):
            return -1

        pattern = re.compile(r'^' + self.username + '\s+(\d+)', re.MULTILINE)
        data = open(file_with_limit, 'r').read()
        match = pattern.search(data)
        return int(match.group(1)) if match else -1

    async def count_connections(self) -> int:
        cmd = 'ps -u ' + self.username + ' | grep sshd | wc -l'
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()
        return int(stdout.decode().strip()) if not stderr else 0


class OVPNChecker:
    def __init__(self, username: str) -> None:
        self.username = username
        self.hostname = '127.0.0.1'
        self.port = 7505

    async def count_connections(self) -> int:
        try:
            reader, writer = await asyncio.open_connection(self.hostname, self.port)

            writer.write(b'status\n')
            await writer.drain()

            buffer = b''
            while True:
                data = await reader.read(1024)
                buffer += data

                if b'\r\nEND\r\n' in data or not data:
                    break

            writer.close()
            count = buffer.count(self.username.encode())
            return count // 2 if count > 0 else 0
        except:
            return 0
