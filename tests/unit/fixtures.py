import unittest

from end2 import (
    metadata,
    parameterize,
    setup,
    setup_test,
    teardown,
    teardown_test
)


class TestFixtures(unittest.TestCase):
    @setup
    def setup_(self):
        pass

    @setup_test
    def setup_test_(self):
        pass

    @teardown
    def teardown_(self):
        pass

    @teardown_test
    def teardown_test_(self):
        pass

    @metadata(tags=['a', 'b', 'c'])
    def metadata_(self):
        pass

    @parameterize([
        ('a', 'b', 'c'),
        ('a', 'b', 'c')
    ])
    def parameterize_(self):
        pass

    def test_setup(self):
        self.assertTrue(hasattr(self.setup_, 'setup'))

    def test_setup_test(self):
        self.assertTrue(hasattr(self.setup_test_, 'setup_test'))

    def test_teardown(self):
        self.assertTrue(hasattr(self.teardown_, 'teardown'))

    def test_teardown_test(self):
        self.assertTrue(hasattr(self.teardown_test_, 'teardown_test'))

    def test_metadata(self):
        self.assertTrue(hasattr(self.metadata_, 'metadata'))
        self.assertEqual(self.metadata_.metadata['tags'], ['a', 'b', 'c'])

    def test_parameterize(self):
        self.assertTrue(hasattr(self.parameterize_, 'names'))
        self.assertTrue(hasattr(self.parameterize_, 'parameterized_list'))
        self.assertEqual(len(self.parameterize_.names), 2)
        self.assertEqual(len(self.parameterize_.parameterized_list), 2)
