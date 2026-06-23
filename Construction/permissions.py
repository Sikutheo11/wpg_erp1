# Construction/permissions.py


# ======================================================
# CONSTRUCTION ROLE PERMISSIONS
# ======================================================


CONSTRUCTION_ROLES = {


    # ==================================================
    # CONSTRUCTION MANAGER
    # ==================================================

    "Construction Manager": [

        # Project
        "construction.view_project",
        "construction.add_project",
        "construction.change_project",

        # Site
        "construction.view_site",
        "construction.add_site",
        "construction.change_site",

        # Task
        "construction.view_task",
        "construction.add_task",
        "construction.change_task",

        # Materials
        "construction.view_constructionmaterial",
        "construction.add_constructionmaterial",
        "construction.change_constructionmaterial",

        # Assets
        "construction.view_constructionassetusage",
        "construction.add_constructionassetusage",

        # Labour
        "construction.view_constructionlabour",
        "construction.add_constructionlabour",
        "construction.change_constructionlabour",

        # Expenses
        "construction.view_constructionexpense",
        "construction.add_constructionexpense",
        "construction.change_constructionexpense",

    ],




    # ==================================================
    # SITE ENGINEER
    # ==================================================

    "Site Engineer": [


        # Project view only
        "construction.view_project",


        # Site
        "construction.view_site",
        "construction.change_site",


        # Tasks
        "construction.view_task",
        "construction.add_task",
        "construction.change_task",


        # Material usage
        "construction.view_constructionmaterial",
        "construction.add_constructionmaterial",


        # Asset usage
        "construction.view_constructionassetusage",
        "construction.add_constructionassetusage",


    ],





    # ==================================================
    # PROJECT SUPERVISOR
    # ==================================================

    "Project Supervisor": [
        "construction.view_project",
        "construction.view_site",
        "construction.change_site",
        "construction.view_task",
        "construction.add_task",
        "construction.change_task",
        "construction.view_constructionmaterial",
    ],





    # ==================================================
    # ACCOUNTANT
    # ==================================================

    "Construction Accountant": [


        "construction.view_project",


        "construction.view_constructionexpense",
        "construction.add_constructionexpense",
        "construction.change_constructionexpense",


        "construction.view_constructionlabour",


        "construction.view_constructionmaterial",


    ],





    # ==================================================
    # VIEW ONLY USER
    # ==================================================

    "Construction Viewer": [


        "construction.view_project",

        "construction.view_site",

        "construction.view_task",

        "construction.view_constructionmaterial",

        "construction.view_constructionassetusage",

        "construction.view_constructionlabour",

        "construction.view_constructionexpense",

    ],


}





# ======================================================
# CHECK USER PERMISSION
# ======================================================


def user_has_construction_permission(
    user,
    permission
):

    """
    Check if user has Construction permission
    """

    return user.has_perm(
        permission
    )





# ======================================================
# GET USER CONSTRUCTION PERMISSIONS
# ======================================================


def get_user_construction_permissions(
    user
):

    """
    Return all construction permissions
    user owns
    """

    permissions = []


    for role, perms in CONSTRUCTION_ROLES.items():

        for perm in perms:

            if user.has_perm(
                perm
            ):

                permissions.append(
                    perm
                )


    return permissions