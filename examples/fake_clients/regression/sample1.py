from src import (
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


async def test_11(client, async_client):
    client.logger.info('hi')
    assert await async_client.put({'hi': 11}) is None
    assert await async_client.put({'hi': 12}) is None
    assert await async_client.put({'hi': 13}) is None


def test_12(client, async_client):
    client.logger.info('hi12')
    assert client.post({'hi': 11}) is None
    assert client.post({'hi': 12}) is None
    assert client.post({'hi': 13}) is None


def test_13(client, async_client):
    assert client.get() == client.get()
