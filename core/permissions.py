# core/permissions.py


EXECUTIVE_PERMISSIONS = {


    "sales": {

        "card":
            "sales.view_sale",

        "details":
            [
                "sales.view_invoice",
                "sales.view_customer",
            ]

    },



    "finance": {

        "card":
            "finance.view_income",

        "details":
            [
                "finance.view_expense",
            ]

    },



    "inventory": {

        "card":
            "inventory.view_product",

        "details":
            [
                "inventory.view_stockmovement",
            ]

    },



    "hr": {

        "card":
            "Employee.view_employee",

        "details":
            []

    },



    "construction": {

        "card":
            "Construction.view_project",

        "details":
            []

    },

}