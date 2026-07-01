from .models import Module

def get_user_modules(user):

    # Manager has access to all active modules
    if user.groups.filter(name="Manager").exists():

        return Module.objects.filter(
            is_active=True
        )


    # Other roles follow RoleModule permissions
    groups = user.groups.all()

    modules = Module.objects.filter(
        roles__role__in=groups,
        roles__can_view=True,
        is_active=True,
    ).distinct()


    return modules