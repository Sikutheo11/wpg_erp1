from .services import get_user_modules
from .dashboard_registry import DASHBOARD_REGISTRY
from .executive_dashboard import get_executive_dashboard
from .charts import get_dashboard_charts



def get_dashboard_context(user):


    context = {


        "modules": [],
        "dashboards": {},
        "executive": {},
        "charts":{}


    }



    modules = get_user_modules(user)


    context["modules"] = modules



    for module in modules:


        module_name = module.name.lower()



        dashboard_function = (
            DASHBOARD_REGISTRY.get(module_name)
        )



        if dashboard_function:


            context["dashboards"][module_name] = (
                dashboard_function(user)
            )



    # CEO DASHBOARD

    context["executive"] = get_executive_dashboard(user)
    context["charts"] = get_dashboard_charts(user)



    return context