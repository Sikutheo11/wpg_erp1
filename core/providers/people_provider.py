from .base import BaseProvider
from .registry import ProviderRegistry


@ProviderRegistry.register
class PeopleProvider(BaseProvider):

    code = "PEOPLE"
    name = "People"

    @staticmethod
    def employees():
        try:
            from Employee.models import Employee
            return Employee.objects.count()
        except Exception:
            return 0

    @staticmethod
    def attendance_today():
        try:
            from Employee.models import Attendance
            from django.utils import timezone

            today = timezone.now().date()
            return Attendance.objects.filter(date=today).count()
        except Exception:
            return 0

    @classmethod
    def kpis(cls):
        return {
            "employees": cls.employees(),
            "attendance_today": cls.attendance_today(),
        }

    @classmethod
    def summary(cls):
        return cls.kpis()

    @classmethod
    def dashboard(cls):
        return {"cards": cls.kpis(), "alerts": cls.alerts()}

    @classmethod
    def report(cls, user=None, **kwargs):
        return {
            "title": "People Report",
            "summary": cls.summary(),
            "rows": [],
            "charts": {},
        }

    @classmethod
    def alerts(cls):
        return []