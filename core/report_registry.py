"""
==========================================
WPG BOS
Report Registry
==========================================
"""

from dataclasses import dataclass


@dataclass
class ReportDefinition:
    code: str
    name: str
    provider: callable


class ReportRegistry:

    _registry = {}

    @classmethod
    def register(cls, code, name, provider):

        cls._registry[code] = ReportDefinition(
            code=code,
            name=name,
            provider=provider,
        )

    @classmethod
    def get(cls, code):

        report = cls._registry.get(code)

        if not report:
            raise ValueError(
                f"Report '{code}' is not registered."
            )

        return report

    @classmethod
    def generate(cls, code, user=None, **kwargs):

        report = cls.get(code)

        return report.provider(
            user=user,
            **kwargs,
        )

    @classmethod
    def all(cls):

        return sorted(
            cls._registry.values(),
            key=lambda x: x.name,
        )