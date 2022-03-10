#!/usr/bin/env python3
from asyncio import sleep as aio_sleep
import os
from random import randint
import sys
from time import sleep

sys.path.insert(0, os.path.join('..', '..'))
from src.runner import start_test_run
from src.arg_parser import default_parser


class Client:
    def __init__(self, logger):
        self.logger = logger

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

    async def put(self, payload):
        self.logger.info(payload)
        await self._sleep()
    
    async def delete(self):
        await self._sleep()


if __name__ == '__main__':
    # Run from inside examples\fake_client
    ## --suite regression\\sample4.py::test_11
    ## --suite regression/sample4.py::test_11
    ## --suite regression\\sample4.py::test_11[4]
    ## --suite regression/sample4.py::test_11[4]
    args = default_parser().parse_args()

    def test_parameters(logger, package_object):
        return (Client(logger), AsyncClient(logger)), {}

    results, _ = start_test_run(args, test_parameters)

    exit(results.exit_code)
