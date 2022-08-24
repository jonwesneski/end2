import end2

__run_mode__ = end2.RunMode.PARALLEL


@end2.setup_test
def my_setup_test(client, async_client):
    client.logger.info('running setup test')
    assert client.get() == {}


@end2.teardown
def my_teardown(client, async_client):
    client.logger.info('running teardown')
    assert client.delete() is None


@end2.metadata(tags=['product', 'business'])
async def test_11(client, async_client):
    client.logger.info('hi')
    assert await async_client.put({'hi': 11}) is None
    assert await async_client.put({'hi': 12}) is None
    assert await async_client.put({'hi': 13}) is None


@end2.metadata(tags=['product'])
def test_12(client, async_client):
    client.logger.info('hi12')
    assert client.post({'hi': 11}) is None
    assert client.post({'hi': 12}) is None
    assert client.post({'hi': 13}) is None


def test_13(client, async_client):
    assert client.get() == client.get()
