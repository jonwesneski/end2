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


def test_31(client, async_client):
    client.logger.info('hi')
    assert client.put({}) is None


def test_32(client, async_client):
    client.logger.info('hi12')
    assert client.post({}) is None


async def test_33(client, async_client):
    assert await async_client.get() == await async_client.get()