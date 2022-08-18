import end2

__run_mode__ = end2.RunMode.PARALLEL
__tags__ = ['product']


@end2.setup_test
def my_setup_test(client, async_client):
    client.logger.info('running setup test')
    assert client.get() == {}


@end2.teardown
def my_teardown(client, async_client):
    client.logger.info('running teardown')
    assert client.delete() is None


def test_31(client, async_client):
    client.logger.info('hi')
    assert client.put({'hi': 31}) is None
    assert client.put({'hi': 32}) is None
    assert client.put({'hi': 33}) is None


def test_32(client, async_client, *, end):
    def handler():
        end()
    client.logger.info('hi12')
    assert client.post({'hi': 32}) is None
    client.on(handler)
    assert client.post({'hi': 33}) is None


async def test_33(client, async_client, *, end):
    def handler():
        end()
    client.on(handler)
    assert await async_client.get() == await async_client.get()


async def test_34(client, async_client):
    assert await async_client.get() == await async_client.get()
