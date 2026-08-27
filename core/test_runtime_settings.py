import json
import logging

from django.conf import settings
from django.test import SimpleTestCase

from core.logging import JsonFormatter


class RuntimeSettingsTests(SimpleTestCase):
    def test_default_business_timezone_is_kigali(self):
        self.assertEqual(settings.TIME_ZONE, "Africa/Kigali")

    def test_console_logging_is_configured(self):
        self.assertIn("console", settings.LOGGING["handlers"])
        self.assertIn("console", settings.LOGGING["root"]["handlers"])

    def test_json_formatter_emits_structured_record(self):
        record = logging.LogRecord(
            name="wpg.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=24,
            msg="runtime ready",
            args=(),
            exc_info=None,
        )
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["level"], "INFO")
        self.assertEqual(payload["logger"], "wpg.test")
        self.assertEqual(payload["message"], "runtime ready")
        self.assertIn("timestamp", payload)
