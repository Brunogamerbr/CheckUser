import asyncio
import socket
import json

from typing import Tuple

from .utils import HttpParser
from .command_handler import CommandHandler

from ..utils.logger import logger


class Worker:
    def __init__(self, concurrency: int = 5) -> None:
        self.concurrency = concurrency
        self.tasks = []

        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue()

        self.command_handler = CommandHandler()

    async def _worker(self):
        while True:
            reader, writer = await self.queue.get()

            try:
                await self.handle(reader, writer)
            except Exception as e:
                logger.error(e)

            writer.close()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        data = await reader.read(1024)

        parser = HttpParser.of(data.decode('utf-8'))
        response = json.dumps(
            HttpParser.build_response(
                status=403,
                headers={'Content-Type': 'Application/json'},
                body='{"error": "Forbidden"}',
            ),
            indent=4,
        )

        if not data or not parser.path:
            writer.write(response.encode('utf-8'))
            await writer.drain()

        split = parser.path.split('/')

        command = split[1]
        content = split[2].split('?')[0] if len(split) > 2 else None

        try:
            response = await self.command_handler.handle(command, content)
            response = json.dumps(response, indent=4)
            response = HttpParser.build_response(
                status=200,
                headers={'Content-Type': 'Application/json'},
                body=response,
            )
        except Exception as e:
            response = HttpParser.build_response(
                status=500,
                headers={'Content-Type': 'Application/json'},
                body=json.dumps({'error': str(e)}, indent=4),
            )

        writer.write(response.encode('utf-8'))
        await writer.drain()

    async def put(self, item: Tuple[socket.socket, Tuple[str, int]]):
        await self.queue.put(item)

    async def start(self):
        for _ in range(self.concurrency):
            task = self.loop.create_task(self._worker())
            self.tasks.append(task)

    def stop(self):
        for task in self.tasks:
            task.cancel()

        self.loop.stop()
