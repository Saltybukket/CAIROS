import unittest

from scripts.run_tests import normalize_newlines, run_case


class RunTestsRunnerTests(unittest.TestCase):
    def test_normalize_newlines_accepts_bytes_none_and_strings(self):
        self.assertEqual(normalize_newlines(None), "")
        self.assertEqual(normalize_newlines(b"a\r\nb"), "a\nb")
        self.assertEqual(normalize_newlines("a\r\nb"), "a\nb")

    def test_timeout_result_does_not_crash_on_captured_bytes(self):
        case = {
            "name": "timeout bytes normalization",
            "command": ["python3", "-c", "import sys, time; sys.stdout.buffer.write(b'hello\\r\\n'); sys.stdout.flush(); time.sleep(1)"],
            "timeout": 0.1,
            "expected_exit": 0,
            "expected_contains": ["hello"],
        }
        result = run_case(case, 1, timeout=1)
        self.assertFalse(result["passed"])
        self.assertTrue(result["timeout"])
        self.assertIn("hello\n", result["actual_stdout"])
        self.assertIn("Timed out after", result["actual_stderr"])


if __name__ == "__main__":
    unittest.main()
