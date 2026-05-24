import unittest
from app.services.hermes_core import decide_intent
from app.services.url_validator import validate_base_url
from app.exceptions import InvalidBaseURLError


class TestHermesCore(unittest.TestCase):
    def test_strong_write_words(self):
        decision = decide_intent("帮我续写下一段")
        self.assertEqual(decision.action, "write")
        self.assertTrue(decision.requires_approval)

    def test_weak_write_words_without_question(self):
        decision = decide_intent("写一段开头")
        self.assertEqual(decision.action, "write")
        self.assertTrue(decision.requires_approval)

    def test_weak_write_words_with_question(self):
        decision = decide_intent("这个章节该怎么写？")
        self.assertEqual(decision.action, "chat")
        self.assertFalse(decision.requires_approval)

    def test_general_chat(self):
        decision = decide_intent("分析一下目前故事的伏笔。")
        self.assertEqual(decision.action, "chat")
        self.assertFalse(decision.requires_approval)


class TestURLValidator(unittest.TestCase):
    def test_valid_urls(self):
        # Should not raise exception
        validate_base_url("https://api.openai.com/v1")
        validate_base_url("http://8.8.8.8/v1")

    def test_invalid_scheme(self):
        with self.assertRaises(InvalidBaseURLError):
            validate_base_url("ftp://example.com")

    def test_localhost(self):
        with self.assertRaises(InvalidBaseURLError):
            validate_base_url("http://localhost:8000")

    def test_loopback_ip(self):
        with self.assertRaises(InvalidBaseURLError):
            validate_base_url("http://127.0.0.1:11434")

    def test_private_ip(self):
        with self.assertRaises(InvalidBaseURLError):
            validate_base_url("http://192.168.1.1:11434")
        with self.assertRaises(InvalidBaseURLError):
            validate_base_url("http://10.0.0.1:11434")


if __name__ == "__main__":
    unittest.main()
