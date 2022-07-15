from ..utils import base_cli, Config
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
    '--status',
    action='store_true',
    help='Show server status',
)

base_cli.add_argument(
    '--server-host',
    default='0.0.0.0',
    help='Server host',
)

base_cli.add_argument(
    '--server-port',
    type=int,
    help='Server port',
)

base_cli.add_argument(
    '--server-num-workers',
    default=3,
    type=int,
    help='Server number of workers',
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
                host=args.server_host,
                port=args.server_port,
                workers=args.server_num_workers,
            )
            server.start()

    daemon = ServerDaemon(pidfile='/tmp/server.pid')

    if args.start:
        if args.server_port is None:
            args.server_port = Config().port

        if args.daemon:
            daemon.start()
        else:
            daemon.run()

    if args.stop:
        daemon.stop()

    if args.status:
        if daemon.is_running():
            process_id = daemon.get_pid()
            print('Server is running with PID {}'.format(process_id))
        else:
            print('Server is not running')
