import asyncio
import unittest

from end2 import runner
from end2.enums import Status
from end2.logger import empty_logger
from end2 import exceptions


class TestRunMethod(unittest.TestCase):
    def test_method_passed(self):
        def test_1():
            assert True
        result = runner.run_test_func(empty_logger, test_1)
        self.assertEqual(result.status, Status.PASSED)
        self.assertEqual(result.message, "")
        self.assertIsNotNone(result.end_time)

    def test_method_failed(self):
        def test_2(a):
            assert False
        result = runner.run_test_func(empty_logger, test_2, 1)
        self.assertEqual(result.status, Status.FAILED)
        self.assertNotEqual(result.message, "")
        self.assertIsNotNone(result.end_time)
    
    def test_method_skipped(self):
        def test_3(a, b):
            raise exceptions.SkipTestException("I skip")
        result = runner.run_test_func(empty_logger, test_3, a=1, b=2)
        self.assertEqual(result.status, Status.SKIPPED)
        self.assertEqual(result.message, "I skip")
        self.assertIsNotNone(result.end_time)

    def test_method_ignore_reraises(self):
        def test_4(a, b):
            raise exceptions.IgnoreTestException("Error")
        self.assertRaises(exceptions.IgnoreTestException, test_4, a=1, b=2)
    
    def test_method_encountered_some_other_exception(self):
        def test_4(a, b, c):
            raise Exception("Error")
        result = runner.run_test_func(empty_logger, test_4, 1, 2, 3)
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn("Encountered an exception", result.message)
        self.assertIsNotNone(result.end_time)


class TestRunMethodAsync(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.loop = asyncio.get_event_loop()

    def test_async_method_passed(self):
        async def test_1():
            assert True
        result = self.loop.run_until_complete(runner.run_async_test_func(empty_logger, test_1))
        self.assertEqual(result.status, Status.PASSED)
        self.assertEqual(result.message, "")
        self.assertIsNotNone(result.end_time)

    def test_async_method_failed(self):
        async def test_2(a):
            assert False
        result = self.loop.run_until_complete(runner.run_async_test_func(empty_logger, test_2, 1))
        self.assertEqual(result.status, Status.FAILED)
        self.assertNotEqual(result.message, "")
        self.assertIsNotNone(result.end_time)
        
    def test_async_method_skipped(self):
        async def test_3(a, b):
            raise exceptions.SkipTestException("I skip")
        result = self.loop.run_until_complete(runner.run_async_test_func(empty_logger, test_3, a=1, b=2))
        self.assertEqual(result.status, Status.SKIPPED) and self.assertEqual(result.message, "I skip") 
        self.assertIsNotNone(result.end_time)

    def test_async_method_ignore_reraises(self):
        async def test_4():
            raise exceptions.IgnoreTestException("Error")

        def run_to_completion():
            return self.loop.run_until_complete(runner.run_async_test_func(empty_logger, test_4))

        self.assertRaises(exceptions.IgnoreTestException, run_to_completion)
        
    def test_async_method_encountered_some_other_exception(self):
        async def test_4(a, b, c):
            raise Exception("Error")
        result = self.loop.run_until_complete(runner.run_async_test_func(empty_logger, test_4, 1, 2, 3))
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn("Encountered an exception", result.message)
        self.assertIsNotNone(result.end_time)
