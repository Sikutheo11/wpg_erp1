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
        "Construction.view_project",
        "Construction.add_project",
        "Construction.change_project",

        # Site
        "Construction.view_site",
        "Construction.add_site",
        "Construction.change_site",

        # Task
        "Construction.view_task",
        "Construction.add_task",
        "Construction.change_task",

        # Materials
        "Construction.view_constructionmaterial",
        "Construction.add_constructionmaterial",
        "Construction.change_constructionmaterial",

        # Assets
        "Construction.view_constructionassetusage",
        "Construction.add_constructionassetusage",

        # Labour
        "Construction.view_constructionlabour",
        "Construction.add_constructionlabour",
        "Construction.change_constructionlabour",

        # Expenses
        "Construction.view_constructionexpense",
        "Construction.add_constructionexpense",
        "Construction.change_constructionexpense",

    ],




    # ==================================================
    # SITE ENGINEER
    # ==================================================

    "Site Engineer": [


        # Project view only
        "Construction.view_project",


        # Site
        "Construction.view_site",
        "Construction.change_site",


        # Tasks
        "Construction.view_task",
        "Construction.add_task",
        "Construction.change_task",


        # Material usage
        "Construction.view_constructionmaterial",
        "Construction.add_constructionmaterial",


        # Asset usage
        "Construction.view_constructionassetusage",
        "Construction.add_constructionassetusage",


    ],





    # ==================================================
    # PROJECT SUPERVISOR
    # ==================================================

    "Project Supervisor": [
        "Construction.view_project",
        "Construction.view_site",
        "Construction.change_site",
        "Construction.view_task",
        "Construction.add_task",
        "Construction.change_task",
        "Construction.view_constructionmaterial",
    ],





    # ==================================================
    # ACCOUNTANT
    # ==================================================

    "Construction Accountant": [


        "Construction.view_project",


        "Construction.view_constructionexpense",
        "Construction.add_constructionexpense",
        "Construction.change_constructionexpense",


        "Construction.view_constructionlabour",


        "Construction.view_constructionmaterial",


    ],





    # ==================================================
    # VIEW ONLY USER
    # ==================================================

    "Construction Viewer": [


        "Construction.view_project",

        "Construction.view_site",

        "Construction.view_task",

        "Construction.view_constructionmaterial",

        "Construction.view_constructionassetusage",

        "Construction.view_constructionlabour",

        "Construction.view_constructionexpense",

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