from django.shortcuts import redirect


def redirect_by_role(user):

    # Super Admin
    if user.is_superuser:

        return redirect(
            "core:dashboard"
        )


    # Groups (Roles)

    groups = user.groups.values_list(
        "name",
        flat=True
    )


    if "Construction Manager" in groups:

        return redirect(
            "construction:dashboard"
        )


    if "Finance Manager" in groups:

        return redirect(
            "finance:dashboard"
        )


    if "Store Keeper" in groups:

        return redirect(
            "inventory:dashboard"
        )


    if "Customer" in groups:

        return redirect(
            "accounts:customer_dashboard"
        )


    # Default

    return redirect(
        "core:dashboard"
    )