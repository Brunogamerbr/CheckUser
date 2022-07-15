import typing as t

# import os

import asyncio


class SSHManager:
    def __init__(self, username: str) -> None:
        self.username = username

        self.list_of_pid = []
        self.loop = asyncio.get_event_loop()

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

        return (
            [
                line.split(':')[0]
                for line in stdout.decode().splitlines()
                if int(line.split(':')[2]) >= 1000
            ]
            if not stderr.decode()
            else []
        )

    @staticmethod
    async def count_all_connections() -> int:
        command = 'ps -u %s'
        count = 0

        for user in await SSHManager.get_all_users():
            result = await asyncio.create_subprocess_shell(
                command % user,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await result.communicate()

            if not stderr.decode():
                data = stdout.decode().splitlines()[1:]
                count += len([line for line in data if 'sshd' in line])

        return count


# loop = asyncio.get_event_loop()

# print(loop.run_until_complete(SSHManager.total_all_connections()))

# exit()
