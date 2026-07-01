DASHBOARD_REGISTRY = {}


def register_dashboard(name, dashboard_function):
    DASHBOARD_REGISTRY[name] = dashboard_function



def get_registered_dashboards():
    return DASHBOARD_REGISTRY