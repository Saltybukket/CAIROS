import io
import urllib.error
import unittest

from cairos.ai.base import _format_http_error, _format_network_error


def config(endpoint="https://openrouter.ai/api/v1", model="openai/gpt-4.1-mini"):
    return {
        "active_ai_profile": "openrouter-paid",
        "ai": {
            "provider": "openai",
            "model": model,
            "endpoint": endpoint,
            "api_key_env": "OPENROUTER_API_KEY",
        },
    }


def http_error(code: int, body: str):
    return urllib.error.HTTPError("https://example.test", code, "error", {}, io.BytesIO(body.encode("utf-8")))


class AIErrorFormattingTests(unittest.TestCase):
    def test_openrouter_402_json_body(self):
        text = _format_http_error(
            "OpenAI-compatible backend",
            http_error(402, '{"error":{"message":"Insufficient credits.","code":402}}'),
            config(),
            '{"error":{"message":"Insufficient credits.","code":402}}',
        )
        self.assertIn("Payment required / insufficient credits", text)
        self.assertIn("Insufficient credits", text)
        self.assertIn("provider: openai", text)
        self.assertIn("model: openai/gpt-4.1-mini", text)
        self.assertIn("api_key_env: OPENROUTER_API_KEY", text)
        self.assertIn("use-openrouter-free", text)

    def test_429_guidance(self):
        text = _format_http_error("OpenAI-compatible backend", http_error(429, "slow down"), config(), "slow down")
        self.assertIn("Rate limit, quota, or usage limit reached", text)
        self.assertIn("billing", text)

    def test_401_403_404_and_network(self):
        self.assertIn("invalid", _format_http_error("backend", http_error(401, ""), config(), ""))
        self.assertIn("Forbidden", _format_http_error("backend", http_error(403, ""), config(), ""))
        self.assertIn("Model or endpoint not found", _format_http_error("backend", http_error(404, ""), config(), ""))
        self.assertIn("proxy", _format_network_error("backend", urllib.error.URLError("offline"), config()))


if __name__ == "__main__":
    unittest.main()
