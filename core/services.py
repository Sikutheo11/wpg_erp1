from .models import Module

def get_user_modules(user):

    roles = user.groups.all()


    modules = Module.objects.filter(
        roles__role__in=roles,
        roles__can_view=True,
        is_active=True
    ).distinct()


    return modules