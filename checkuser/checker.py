import socket
import subprocess
import datetime as dt
import re
import os


def get_all_users() -> list:
    with open('/etc/passwd') as f:
        return [line.split(':')[0] for line in f.readlines() if int(line.split(':')[2]) >= 1000]


class SSHChecker:
    def __init__(self, username: str) -> None:
        self.username = username

    def expiration_date(self) -> str:
        cmd = 'chage -l ' + self.username
        proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if stderr:
            return 'never'

        pattern = re.compile(r'Account expires\s+:\s+(.*)|Conta expira\s+:\s+(.*)')
        match = pattern.search(stdout.decode('utf-8'))
        date = match.group(1) or match.group(2)
        return (
            dt.datetime.strptime(date, '%b %d, %Y').strftime('%d/%m/%Y')
            if date and date != 'never'
            else 'never'
        )

    def expiration_days(self, date: str = None) -> int:
        if not date:
            date = self.expiration_date()

        if date == 'never':
            return -1

        try:
            today = dt.datetime.now()
            return (dt.datetime.strptime(date, '%d/%m/%Y') - today).days
        except ValueError:
            return -1

    def limit_connections(self) -> int:
        cmd = 'command -v vps-cli > /dev/null 2>&1'

        if os.system(cmd) == 0:
            cmd = 'vps-cli -u %s -s' % self.username
            proc = subprocess.Popen(
                cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = proc.communicate()
            if stderr:
                return -1

            pattern = re.compile(r'Limit connections:\s+(.*)')
            match = pattern.search(stdout.decode('utf-8'))
            return int(match.group(1)) if match else -1

        file_with_limit = '/root/usuarios.db'

        if not os.path.exists(file_with_limit):
            return -1

        pattern = re.compile(r'^' + self.username + '\s+(\d+)', re.MULTILINE)
        data = open(file_with_limit, 'r').read()
        match = pattern.search(data)
        return int(match.group(1)) if match else -1

    def count_connections(self) -> int:
        cmd = 'ps -u ' + self.username + ' | grep sshd | wc -l'
        proc = subprocess.Popen(
            cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = proc.communicate()
        return int(stdout.decode().strip()) if not stderr else 0

    def stop_connections(self) -> None:
        cmd = 'pkill -9 -u ' + self.username
        proc = subprocess.Popen(
            cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        proc.communicate()

    @staticmethod
    def count_all_connections() -> int:
        all_users = get_all_users()
        tasks = [SSHChecker(user).count_connections() for user in all_users]
        return sum(tasks)


class OVPNChecker:
    def __init__(self, username: str) -> None:
        self.username = username
        self.hostname = '127.0.0.1'
        self.port = 7505

    def count_connections(self) -> int:
        try:
            soc = socket.create_connection((self.hostname, self.port), timeout=5)
            soc.send(b'status\n')

            buffer = b''
            while True:
                data = soc.recv(1024)
                buffer += data

                if b'\r\nEND\r\n' in data or not data:
                    break

            soc.close()
            count = buffer.count(self.username.encode())
            return count // 2 if count > 0 else 0
        except:
            return 0

    def stop_connections(self) -> None:
        try:
            soc = socket.create_connection((self.hostname, self.port), timeout=5)
            soc.send(b'kill ' + self.username.encode() + b'\n')
            soc.close()
        except:
            pass

    @staticmethod
    def count_all_connections() -> int:
        all_users = get_all_users()
        tasks = [OVPNChecker(user).count_connections() for user in all_users]
        return sum(tasks)
