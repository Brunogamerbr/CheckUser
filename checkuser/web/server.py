import resource
import asyncio

from .async_worker import Worker
from ..utils import logger


try:
    resource.setrlimit(resource.RLIMIT_NOFILE, (65536, 65536))
except Exception as e:
    from ..utils.logger import logger

    logger.error('Error: {}'.format(e))


class Server:
    def __init__(self, host: str, port: int, workers: int = 10):
        self.host = host
        self.port = port
        self.workers = workers

        self.loop = asyncio.get_event_loop()
        self.worker = Worker(workers)

        self.server = None

    async def _start(self):
        logger.info(f'Listening on {self.host}:{self.port}')
        self.server = await asyncio.start_server(self._handle, self.host, self.port)

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await self.worker.queue.put((reader, writer))

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
