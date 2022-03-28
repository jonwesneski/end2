import unittest

import end2


class TestFixtures(unittest.TestCase):
    @end2.setup
    def setup_(self):
        pass

    @end2.setup_test
    def setup_test_(self):
        pass

    @end2.teardown
    def teardown_(self):
        pass

    @end2.teardown_test
    def teardown_test_(self):
        pass

    @end2.metadata(tags=['a', 'b', 'c'])
    def metadata_(self):
        pass

    @end2.parameterize([
        ('a', 'b', 'c'),
        ('a', 'b', 'c')
    ])
    def parameterize_(self):
        pass

    @end2.on_failures_in_module
    def on_failures_in_module_(self):
        pass

    def my_failure_step(self, *args, **kwargs):
        self.abc = True

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

    def test_on_failures_in_module(self):
        self.assertTrue(hasattr(self.on_failures_in_module_, 'on_failures_in_module'))

    def test_on_test_failure(self):
        @end2.on_test_failure(self.my_failure_step)
        def dd():
            pass
        dd.on_test_failure()
        self.assertTrue(hasattr(self, 'abc'))
