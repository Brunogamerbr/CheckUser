import time
import threading

from ..utils import base_cli
from ..utils.daemon import Daemon
from ..web import Server

base_cli.add_argument(
    '--start',
    action='store_true',
    help='Start server',
)

base_cli.add_argument(
    '--stop',
    action='store_true',
    help='Stop server',
)
base_cli.add_argument(
    '--restart',
    action='store_true',
    help='Restart server',
)
base_cli.add_argument(
    '--status',
    action='store_true',
    help='Show server status',
)

base_cli.add_argument(
    '--host',
    default='0.0.0.0',
    help='Server host',
)

base_cli.add_argument(
    '--port',
    type=int,
    default=5000,
    help='Server port',
)

base_cli.add_argument(
    '--workers',
    default=32,
    type=int,
    help='Server number of workers (default: %(default)s)',
)

base_cli.add_argument(
    '--daemon',
    action='store_true',
    help='Daemonize',
)


class Restart:
    def __init__(self, server) -> None:
        self._server = server
        self._interval = 10
        self._thread = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError('Restart thread already running')

        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()

    def _run(self) -> None:
        while True:
            time.sleep(self._interval)
            self._server.restart()


def args_handler(args):
    class ServerDaemon(Daemon):
        def run(self):
            server = Server(
                host=args.host,
                port=args.port,
                workers=args.workers,
            )
            server.start()

    daemon = ServerDaemon(pidfile='/tmp/server.pid')

    if args.start:
        restart = Restart(server=daemon)
        restart.start()

        if args.daemon:
            daemon.start()
        else:
            daemon.run()

    if args.stop:
        daemon.stop()

    if args.restart:
        daemon.restart()

    if args.status:
        if daemon.is_running():
            process_id = daemon.get_pid()
            print('Server is running with PID {}'.format(process_id))
        else:
            print('Server is not running')
