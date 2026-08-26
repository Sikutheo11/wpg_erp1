from django.conf import settings
from django.test import SimpleTestCase


class SecurityDefaultsTests(SimpleTestCase):
    def test_rest_framework_is_private_by_default(self):
        permission_classes = settings.REST_FRAMEWORK[
            "DEFAULT_PERMISSION_CLASSES"
        ]

        self.assertIn(
            "rest_framework.permissions.IsAuthenticated",
            permission_classes,
        )
        self.assertNotIn(
            "rest_framework.permissions.AllowAny",
            permission_classes,
        )
