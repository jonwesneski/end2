#!/usr/bin/env python3
from asyncio import sleep as aio_sleep
import os
from random import randint
import sys
from time import sleep

sys.path.insert(0, os.path.join('..', '..'))
from end2.runner import start_test_run
from end2.arg_parser import default_parser



class SimplePubSub:
    def __init__(self) -> None:
        self.subscribers = {}

    def unsubscribe(self, event: str) -> None:
        self.subscribers.pop(event, None)

    def subscribe(self, event: str, callback) -> None:
        self.subscribers[event] = callback

    def publish(self, event: str, *args) -> None:
        if event in self.subscribers.keys():
            self.subscribers[event](*args)


class Client:
    def __init__(self, logger):
        self.logger = logger
        self.pub_sub = SimplePubSub()

    @staticmethod
    def _sleep():
        sleep(randint(1, 3))

    def get(self):
        self._sleep()
        return {}

    def post(self, payload):
        self.logger.info(payload)
        self._sleep()

    def put(self, payload):
        self.logger.info(payload)
        self._sleep()
    
    def delete(self):
        self._sleep()

    def on(self, handler):
        self.pub_sub.subscribe("event", handler)


class AsyncClient:
    def __init__(self, logger):
        self.logger = logger

    @staticmethod
    async def _sleep():
        await aio_sleep(randint(1, 3))

    async def get(self):
        await self._sleep()
        return {}

    async def post(self, payload):
        self.logger.info(payload)
        await self._sleep()
        return {}

    async def put(self, payload):
        self.logger.info(payload)
        await self._sleep()
    
    async def delete(self):
        await self._sleep()


if __name__ == '__main__':
    args = default_parser().parse_args()

    def test_parameters(logger, package_object):
        return (Client(logger), AsyncClient(logger)), {}

    results, failed_imports = start_test_run(args, test_parameters)

    print(failed_imports)
    exit(results.exit_code)
