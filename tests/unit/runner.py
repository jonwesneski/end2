import asyncio
import unittest

from end2 import runner
from end2.constants import Status
from end2.logger import empty_logger
from end2 import exceptions


class TestRunMethod(unittest.TestCase):
    def test_method_passed(self):
        def test_1():
            assert True
        result = runner.run_test_func(empty_logger, None, test_1)
        self.assertEqual(result.status, Status.PASSED)
        self.assertEqual(result.message, "")
        self.assertIsNotNone(result.end_time)

    def test_method_failed(self):
        def test_2(a):
            assert False
        result = runner.run_test_func(empty_logger, None, test_2, 1)
        self.assertEqual(result.status, Status.FAILED)
        self.assertNotEqual(result.message, "")
        self.assertIsNotNone(result.end_time)
    
    def test_method_skipped(self):
        def test_3(a, b):
            raise exceptions.SkipTestException("I skip")
        result = runner.run_test_func(empty_logger, None, test_3, a=1, b=2)
        self.assertEqual(result.status, Status.SKIPPED)
        self.assertEqual(result.message, "I skip")
        self.assertIsNotNone(result.end_time)

    def test_method_ignore_reraises(self):
        def test_4(a, b):
            raise exceptions.IgnoreTestException("Error")
        with self.assertRaises(exceptions.IgnoreTestException):
            runner.run_test_func(empty_logger, None, test_4, 1, 2)
    
    def test_method_encountered_some_other_exception(self):
        def test_4(a, b, c):
            raise Exception("Error")
        result = runner.run_test_func(empty_logger, None, test_4, 1, 2, 3)
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn("Encountered an exception", result.message)
        self.assertIsNotNone(result.end_time)

    def test_method_end_callback(self):
        def test_4(*, end):
            end()
        ender = runner.Ender()
        end = ender.create()
        result = runner.run_test_func(empty_logger, ender, test_4, end=end)
        self.assertEqual(result.status, Status.PASSED)

    def test_method_end_fail_callback(self):
        expected_message = "i fail"
        def test_4(*, end):
            end.fail(expected_message)
        ender = runner.Ender()
        end = ender.create()
        result = runner.run_test_func(empty_logger, ender, test_4, end=end)
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn(expected_message, result.message)

    def test_method_end_callback_timeout(self):
        expected_timeout = 1.0
        def test_4(*, end):
            pass
        ender = runner.Ender(expected_timeout)
        end = ender.create()
        result = runner.run_test_func(empty_logger, ender, test_4, end=end)
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn(str(expected_timeout), result.message)


class TestRunMethodAsync(unittest.TestCase):
    def test_async_method_passed(self):
        async def test_1():
            await asyncio.sleep(0.1)
            assert True
        result = asyncio.run(runner.run_async_test_func(empty_logger, test_1))
        self.assertEqual(result.status, Status.PASSED)
        self.assertEqual(result.message, "")
        self.assertIsNotNone(result.end_time)

    def test_async_method_failed(self):
        async def test_2(a):
            await asyncio.sleep(0.1)
            assert False
        result = asyncio.run(runner.run_async_test_func(empty_logger, test_2, 1))
        self.assertEqual(result.status, Status.FAILED)
        self.assertNotEqual(result.message, "")
        self.assertIsNotNone(result.end_time)
        
    def test_async_method_skipped(self):
        async def test_3(a, b):
            await asyncio.sleep(0.1)
            raise exceptions.SkipTestException("I skip")
        result = asyncio.run(runner.run_async_test_func(empty_logger, test_3, a=1, b=2))
        self.assertEqual(result.status, Status.SKIPPED) and self.assertEqual(result.message, "I skip") 
        self.assertIsNotNone(result.end_time)

    def test_async_method_ignore_reraises(self):
        async def test_4():
            await asyncio.sleep(0.1)
            raise exceptions.IgnoreTestException("Error")

        def run_to_completion():
            return asyncio.run(runner.run_async_test_func(empty_logger, test_4))

        self.assertRaises(exceptions.IgnoreTestException, run_to_completion)
        
    def test_async_method_encountered_some_other_exception(self):
        async def test_4(a, b, c):
            await asyncio.sleep(0.1)
            raise Exception("Error")
        result = asyncio.run(runner.run_async_test_func(empty_logger, test_4, 1, 2, 3))
        self.assertEqual(result.status, Status.FAILED)
        self.assertIn("Encountered an exception", result.message)
        self.assertIsNotNone(result.end_time)
