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


def test_21(client, async_client, *, step):
    client.logger.info('hi')
    step("my first step", lambda x: x is None, client.put, {'hi': 21})
    result = step("my second step", None, client.put, {'hi': 22})
    step("my second step", None, client.put, {'hi': 23})
    assert result is None


async def test_22(client, async_client, *, step):
    client.logger.info('hi22')
    await step("my first step", lambda x: x == {}, async_client.post, {'hi': 21})
    result = await step("my second step", None, async_client.post, {'hi': 22})
    await step("my third step", None, async_client.post, {'hi': 23})
    assert result == {}


def test_23(client, async_client):
    assert client.get() == client.get()
