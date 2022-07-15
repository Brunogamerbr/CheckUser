import typing as t

# import os

import asyncio


class SSHManager:
    async def count_connections(self, username: str) -> int:
        command = 'ps -u {}'.format(username)
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if stderr:
            return 0

        data = stdout.decode().splitlines()[1:]
        return len(list(filter(lambda x: 'sshd' in x, data)))

    @property
    def total_connections(self) -> int:
        return len(self.list_of_pid)

    async def get_pids(self) -> t.List[int]:
        command = 'ps -u {}'.format(self.username)
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if stderr.decode():
            return []

        data = stdout.decode().splitlines()[1:]
        pids = [int(line.split()[0]) for line in data]
        return pids

    async def kill_connection(self) -> None:
        for pid in self.list_of_pid:
            command = 'kill -9 {}'.format(pid)
            await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        self.list_of_pid = []

    async def get_expiration_date(self) -> t.Optional[str]:
        command = 'chage -l {}'.format(self.username)
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()
        return (
            stdout.decode().split('Account expires: ')[1].split()[0].strip()
            if not stderr.decode()
            else None
        )

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
