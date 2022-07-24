import socket
import resource
import typing as t

from .worker import Handler
from . import logger

try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
except Exception as e:
    from . import logger

    logger.error('Error: {}'.format(e))


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_running = False

    def handle(self, client: socket.socket, addr: t.Tuple[str, int]) -> None:
        handler = Handler(client, addr)
        handler.daemon = True
        handler.start()

    def start(self) -> None:
        self.socket.bind((self.host, self.port))
        self.socket.listen(0)
        self.socket.settimeout(0.1)
        self.is_running = True

        logger.info('Server started on %s:%d', self.host, self.port)

        while self.is_running:
            try:
                client, addr = self.socket.accept()
                self.handle(client, addr)
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                logger.exception('Error: {}'.format(e))
                continue

    def stop(self) -> None:
        self.is_running = False
        self.socket.close()
