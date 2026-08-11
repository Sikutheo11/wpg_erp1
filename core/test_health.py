from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import TestCase
from django.urls import reverse


class HealthCheckTests(TestCase):
    def test_health_check_reports_application_and_database_ready(
        self,
    ):
        response = self.client.get(
            reverse("core:health_check")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "database": "ok",
            },
        )

    @patch(
        "core.views.connection.cursor",
        side_effect=OperationalError(
            "Database unavailable"
        ),
    )
    def test_health_check_returns_503_when_database_is_unavailable(
        self,
        unused_cursor,
    ):
        response = self.client.get(
            reverse("core:health_check")
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "unavailable",
                "database": "unavailable",
            },
        )