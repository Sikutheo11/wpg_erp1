from .models import Module

def register_module(
    name,
    url_name,
    icon="",
    permission=""
):

    module, created = Module.objects.get_or_create(
        name=name,
        defaults={
            "url_name": url_name,
            "icon": icon,
            "permission": permission,
            "is_active": True,
        }
    )

    return module