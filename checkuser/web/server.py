import resource
import asyncio

from .async_worker import Worker
from ..utils import logger

try:
    __import__('uvloop').install()
except ImportError:
    pass


try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
except Exception as e:
    from ..utils.logger import logger

    logger.error('Error: {}'.format(e))


class Server:
    def __init__(self, host: str, port: int, workers: int = 10):
        self.host = host
        self.port = port
        self.workers = workers

        self.loop = asyncio.get_event_loop()
        self.worker = Worker(concurrency=workers, loop=self.loop)

        self.server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await self.worker.queue.put((reader, writer))

    async def _start(self):
        self.server = await asyncio.start_server(self._handle, self.host, self.port)
        logger.info('Listening on {}:{}'.format(self.host, self.port))

    def start(self):
        try:
            self.loop.create_task(self.worker.start())
            self.loop.create_task(self._start())
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass

        finally:
            logger.info('Closing server')
            self.worker.stop()

            if self.server:
                self.server.close()

            self.loop.run_until_complete(self.server.wait_closed())
            self.loop.close()
