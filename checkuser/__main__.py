import sys
import logging

from . import args
from .server import Server
from .daemon import Daemon

args.add_argument('--host', type=str, help='Host to listen', default='0.0.0.0')
args.add_argument('--port', '-p', type=int, help='Port', default=5000)

args.add_argument('--daemon', '-d', action='store_true', help='Run as daemon')
args.add_argument('--start', '-s', action='store_true', help='Start server')
args.add_argument('--stop', '-t', action='store_true', help='Stop server')
args.add_argument('--restart', '-r', action='store_true', help='Restart server')


def main():
    parser = args.parse_args()

    class ServerDaemon(Daemon):
        def __init__(self):
            super().__init__('/tmp/checkuser.pid')

        def run(self):
            server = Server(host=parser.host, port=parser.port)
            server.start()

    daemon = ServerDaemon()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
    )

    if parser.start:
        if parser.daemon:
            daemon.start()
        else:
            daemon.run()
    elif parser.stop:
        daemon.stop()
    elif parser.restart:
        daemon.restart()
    else:
        args.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
