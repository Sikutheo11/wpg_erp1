from django.test import TestCase
from django.urls import reverse


class PublicHomepageTests(TestCase):
    def test_homepage_loads_successfully(self):
        response = self.client.get(
            reverse("core:home")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "core/home.html",
        )
        self.assertContains(
            response,
            "WPG Marketplace",
        )