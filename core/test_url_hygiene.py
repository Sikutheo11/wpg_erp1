import ast
from importlib import import_module

from django.conf import settings
from django.test import SimpleTestCase


URL_MODULES = (
    "Construction.urls",
    "Employee.urls",
    "accounts.urls",
    "agriculture.urls",
    "core.urls",
    "ecommerce.urls",
    "finance.urls",
    "furniture.urls",
    "inventory.urls",
    "orders.urls",
    "sales.urls",
)


class UrlHygieneTests(SimpleTestCase):
    def test_app_url_modules_have_no_duplicate_routes_or_names(self):
        problems = []

        for module_name in URL_MODULES:
            module = import_module(module_name)
            routes = {}
            names = {}

            for pattern in module.urlpatterns:
                route = str(pattern.pattern)
                name = getattr(pattern, "name", None)

                if route in routes:
                    problems.append(
                        f"{module_name}: duplicate route {route!r}"
                    )
                else:
                    routes[route] = pattern

                if name:
                    if name in names:
                        problems.append(
                            f"{module_name}: duplicate name {name!r}"
                        )
                    else:
                        names[name] = pattern

        self.assertEqual(problems, [], "\n".join(problems))

    def test_finance_workflow_actions_are_post_only(self):
        required_post_views = {
            "income_declaration_submit",
            "income_declaration_unit_approve",
            "income_declaration_confirm",
            "income_declaration_decide",
            "expense_request_submit",
            "expense_request_manager_approve",
            "expense_request_verify",
            "expense_request_finance_approve",
            "expense_request_director_approve",
            "expense_request_pay",
            "expense_request_decide",
        }
        source = (settings.BASE_DIR / "finance" / "views.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        missing = []

        for view_name in sorted(required_post_views):
            function = functions.get(view_name)
            if function is None:
                missing.append(f"{view_name}: view not found")
                continue

            decorators = {
                decorator.id
                for decorator in function.decorator_list
                if isinstance(decorator, ast.Name)
            }
            if "require_POST" not in decorators:
                missing.append(f"{view_name}: missing @require_POST")

        self.assertEqual(missing, [], "\n".join(missing))
