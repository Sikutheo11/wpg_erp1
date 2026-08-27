from django.test import SimpleTestCase
from django.urls import reverse


class PlannerUrlTests(SimpleTestCase):
    def test_planner_urls_reverse(self):
        self.assertEqual(reverse("furniture:planner_list"), "/furniture/planning/")
        self.assertEqual(reverse("furniture:planner_create"), "/furniture/planning/new/")
        self.assertEqual(reverse("furniture:planner_detail", args=[7]), "/furniture/planning/7/")
