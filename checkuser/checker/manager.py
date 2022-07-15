import typing as t
import os
import asyncio

from datetime import datetime

from ..utils import logger
from .ovpn import OpenVPNManager
from .ssh import SSHManager


class CheckerUserManager:
    def __init__(self, username: str):
        self.username = username
        self.ssh_manager = SSHManager(username)
        self.openvpn_manager = OpenVPNManager()

    async def get_expiration_date(self) -> t.Optional[str]:
        command = 'chage -l %s' % self.username
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()
        return (
            stdout.decode().split('Account expires:')[1].split()[0].strip()
            if not stderr.decode()
            else None
        )

    async def get_expiration_days(self, date: str) -> int:
        if not isinstance(date, str) or date.lower() == 'never':
            return -1

        return (datetime.strptime(date, '%b %d, %Y') - datetime.now()).days

    async def get_connections(self) -> int:
        count = 0

        if await self.openvpn_manager.openvpn_is_running():
            # await self.openvpn_manager.start_manager()
            count += await self.openvpn_manager.count_connections(self.username)

        await self.ssh_manager.get_pids()

        count += self.ssh_manager.total_connections
        return count

    async def get_time_online(self) -> t.Optional[str]:
        command = 'ps -u %s -o etime --no-headers' % self.username
        result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await result.communicate()

        if stderr:
            return None

        return stdout.decode().strip().split()[0] if stdout else None

    async def get_limiter_connection(self) -> int:
        path = '/root/usuarios.db'
        limit_connections = -1

        try:
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        split = line.strip().split()
                        if len(split) == 2 and split[0] == self.username:
                            limit_connections = int(split[1])
                            return limit_connections

            process = await asyncio.create_subprocess_shell(
                'command -v vps-cli',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if stderr.decode():
                return limit_connections

            process = await asyncio.create_subprocess_shell(
                'vps-cli -u %s -s' % self.username,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if stderr.decode():
                return limit_connections

            data = stdout.decode().strip()
            if data != 'User not found':
                limit_connections = int(data.split('Limit connections:')[1].split()[0].strip())

        finally:
            return limit_connections

    async def kill_connection(self) -> None:
        await self.ssh_manager.kill_connection(self.username)
        await self.openvpn_manager.kill_connection(self.username)

    @staticmethod
    async def count_all_connections() -> int:
        ssh_manager = SSHManager()
        openvpn_manager = OpenVPNManager()

        count = 0

        if await openvpn_manager.openvpn_is_running():
            count += await openvpn_manager.count_all_connections()

        count += await ssh_manager.count_all_connections()
        return count


async def check_user(username: str) -> t.Dict[str, t.Any]:
    try:
        checker = CheckerUserManager(username)

        count = await checker.get_connections()
        expiration_date = await checker.get_expiration_date()
        expiration_days = await checker.get_expiration_days(expiration_date)
        limit_connection = await checker.get_limiter_connection()
        time_online = await checker.get_time_online()

        return {
            'username': username,
            'count_connection': count,
            'limit_connection': limit_connection,
            'expiration_date': expiration_date,
            'expiration_days': expiration_days,
            'time_online': time_online,
        }
    except Exception as e:
        logger.exception(e)
        return {'error': str(e)}


async def kill_user(username: str) -> dict:
    result = {
        'success': True,
        'error': None,
    }

    try:
        checker = CheckerUserManager(username)
        await checker.kill_connection()
        return result
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)
        return result


async def count_all_connections() -> dict:
    result = {
        'count': 0,
        'success': True,
    }

    try:
        result['count'] = await CheckerUserManager.count_all_connections()
    except Exception as e:
        result['success'] = False
        result['error'] = str(e)

    return result
