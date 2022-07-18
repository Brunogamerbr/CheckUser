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
