from end2 import (
    RunMode,
    setup_test,
    teardown
)

__run_mode__ = RunMode.PARALLEL


@setup_test
def my_setup_test(client, async_client):
    client.logger.info('running setup test')
    assert client.get() == {}


@teardown
def my_teardown(client, async_client):
    client.logger.info('running teardown')
    assert client.delete() is None


def test_21(client, async_client):
    client.logger.info('hi')
    assert client.put({'hi': 21}) is None
    assert client.put({'hi': 22}) is None
    assert client.put({'hi': 23}) is None


async def test_22(client, async_client):
    client.logger.info('hi22')
    assert await async_client.post({'hi': 21}) is None
    assert await async_client.post({'hi': 22}) is None
    assert await async_client.post({'hi': 23}) is None


def test_23(client, async_client):
    assert client.get() == client.get()
