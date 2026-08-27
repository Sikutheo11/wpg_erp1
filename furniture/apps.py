from django.apps import AppConfig


class FurnitureConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"
    name = "furniture"

    def ready(self):
        # Register planner models under the Furniture app.
        # This keeps the large furniture/models.py stable while allowing
        # makemigrations to discover the new pre-production planner models.
        from . import planner_models  # noqa: F401
