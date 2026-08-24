# ======================================================
# WPG BOS INITIAL DATA
# Business Units, Enterprise Engines, Features, Dashboard Cards
# ======================================================


# ======================================================
# BUSINESS UNITS
# ======================================================

BUSINESS_UNITS = [
    {
        "name": "Furniture & Manufacturing",
        "code": "FURNITURE",
        "description": "Furniture production, manufacturing, doors, windows, interiors and custom production.",
        "icon": "bi bi-chair",
        "order": 1,
    },
    {
        "name": "Construction & Built Environment",
        "code": "CONSTRUCTION",
        "description": "House construction, blueprints, interior design, maintenance and future real estate.",
        "icon": "bi bi-building",
        "order": 2,
    },
    {
        "name": "Agriculture / Poultry",
        "code": "AGRICULTURE",
        "description": "Poultry farming, eggs, chicken meat, feed and future agriculture activities.",
        "icon": "bi bi-egg",
        "order": 3,
    },
    {
        "name": "Marketplace",
        "code": "MARKETPLACE",
        "description": "Online marketplace for furniture, blueprints, eggs, chicken meat, timber, doors and windows.",
        "icon": "bi bi-shop",
        "order": 4,
    },
]


# ======================================================
# ENTERPRISE ENGINES
# ======================================================

ENTERPRISE_ENGINES = [
    {
        "name": "Customer Engine",
        "code": "CUSTOMER",
        "description": "Central customer management used by all business units.",
        "icon": "bi bi-person-lines-fill",
        "order": 1,
    },
    {
        "name": "Order Engine",
        "code": "ORDER",
        "description": "Shared order engine used by Furniture, Marketplace, Agriculture and other business units.",
        "icon": "bi bi-cart-check",
        "order": 2,
    },
    {
        "name": "Quotation Engine",
        "code": "QUOTATION",
        "description": "Quotation and costing engine for furniture, construction and services.",
        "icon": "bi bi-file-earmark-text",
        "order": 3,
    },
    {
        "name": "Inventory Engine",
        "code": "INVENTORY",
        "description": "Central inventory, raw materials, products, warehouses and stock movements.",
        "icon": "bi bi-box-seam",
        "order": 4,
    },
    {
        "name": "Finance & Accounting Engine",
        "code": "FINANCE",
        "description": "Finance, accounting, treasury, income, expenses, payments and investor transparency.",
        "icon": "bi bi-cash-stack",
        "order": 5,
    },
    {
        "name": "People Engine",
        "code": "PEOPLE",
        "description": "Employees, HR, attendance, payroll, performance and people development.",
        "icon": "bi bi-people",
        "order": 6,
    },
    {
        "name": "Asset Engine",
        "code": "ASSET",
        "description": "Company assets, machines, tools, assignments and maintenance.",
        "icon": "bi bi-tools",
        "order": 7,
    },
    {
        "name": "Approval Engine",
        "code": "APPROVAL",
        "description": "Approval workflows across finance, procurement, production and projects.",
        "icon": "bi bi-check2-circle",
        "order": 8,
    },
    {
        "name": "Notification Engine",
        "code": "NOTIFICATION",
        "description": "System notifications and alerts.",
        "icon": "bi bi-bell",
        "order": 9,
    },
    {
        "name": "Audit Engine",
        "code": "AUDIT",
        "description": "Audit trails and transparency logs across the platform.",
        "icon": "bi bi-shield-check",
        "order": 10,
    },
    {
        "name": "Reporting Engine",
        "code": "REPORTING",
        "description": "Dashboards, reports, KPIs and analytics.",
        "icon": "bi bi-graph-up-arrow",
        "order": 11,
    },
]


# ======================================================
# LEGACY MODULES
# Keep temporarily while old dashboard/sidebar is being refactored.
# Later these will be removed after BusinessUnit/Engine sidebar is complete.
# ======================================================

MODULES = [
    {
        "name": "Furniture & Manufacturing",
        "code": "FURNITURE",
        "icon": "bi bi-chair",
        "url_name": "",
        "permission": "",
        "order": 1,
    },
    {
        "name": "Construction",
        "code": "CONSTRUCTION",
        "icon": "bi bi-building",
        "url_name": "",
        "permission": "",
        "order": 2,
    },
    {
        "name": "Agriculture",
        "code": "AGRICULTURE",
        "icon": "bi bi-egg",
        "url_name": "",
        "permission": "",
        "order": 3,
    },
    {
        "name": "Marketplace",
        "code": "MARKETPLACE",
        "icon": "bi bi-shop",
        "url_name": "",
        "permission": "",
        "order": 4,
    },
    {
        "name": "Inventory Engine",
        "code": "INVENTORY",
        "icon": "bi bi-box-seam",
        "url_name": "",
        "permission": "",
        "order": 5,
    },
    {
        "name": "Finance Engine",
        "code": "FINANCE",
        "icon": "bi bi-cash-stack",
        "url_name": "",
        "permission": "",
        "order": 6,
    },
    {
        "name": "People Engine",
        "code": "PEOPLE",
        "icon": "bi bi-people",
        "url_name": "",
        "permission": "",
        "order": 7,
    },
]


# ======================================================
# FEATURES
# A feature belongs either to a Business Unit or to an Enterprise Engine.
# ======================================================

BUSINESS_UNIT_FEATURES = {
    "FURNITURE": [
        ("Dashboard", "FURNITURE_DASHBOARD", "furniture:production_job_list", "bi bi-speedometer2", 1),
        ("Production Jobs", "FURNITURE_PRODUCTION_JOBS", "furniture:production_job_list", "bi bi-list-task", 2),
        ("Quotations", "FURNITURE_QUOTATIONS", "furniture:quotation_list", "bi bi-file-earmark-text", 3),
        ("Materials", "FURNITURE_MATERIALS", "furniture:material_list", "bi bi-tree", 4),
        ("Outputs", "FURNITURE_OUTPUTS", "furniture:output_list", "bi bi-box-arrow-up", 5),
        ("Legacy Orders", "FURNITURE_ORDERS", "furniture:order_list", "bi bi-cart", 6),
        ("Production Tasks", "FURNITURE_TASKS", "furniture:production_task_list", "bi bi-check2-square", 7),
        ("My Tasks", "FURNITURE_MY_TASKS", "furniture:my_production_tasks", "bi bi-person-check", 8),
        ("Labour", "FURNITURE_LABOUR", "furniture:labour_list", "bi bi-people", 9),
        ("Machines", "FURNITURE_MACHINES", "furniture:machine_list", "bi bi-gear", 10),
        ("Quality", "FURNITURE_QUALITY", "furniture:quality_inspection_list", "bi bi-shield-check", 11),
        ("Rework", "FURNITURE_REWORK", "furniture:rework_order_list", "bi bi-arrow-repeat", 12),
        ("Reports", "FURNITURE_REPORTS", "furniture:production_reports", "bi bi-bar-chart", 13),
        ("Settings", "FURNITURE_SETTINGS", "furniture:production_settings", "bi bi-sliders", 14),
    ],
    "CONSTRUCTION": [
        ("Dashboard", "CONSTRUCTION_DASHBOARD", "Construction:construction_dashboard", "bi bi-speedometer2", 1),
        ("Projects", "CONSTRUCTION_PROJECTS", "Construction:project_list", "bi bi-kanban", 2),
        ("Sites", "CONSTRUCTION_SITES", "Construction:project_list", "bi bi-geo-alt", 3),
        ("Tasks", "CONSTRUCTION_TASKS", "Construction:project_list", "bi bi-check2-square", 4),
        ("Materials", "CONSTRUCTION_MATERIALS", "Construction:project_list", "bi bi-boxes", 5),
        ("Labour", "CONSTRUCTION_LABOUR", "Construction:project_list", "bi bi-people", 6),
        ("Asset Usage", "CONSTRUCTION_ASSET_USAGE", "Construction:project_list", "bi bi-tools", 7),
        ("Expenses", "CONSTRUCTION_EXPENSES", "Construction:project_list", "bi bi-cash-stack", 8),
        ("Reports", "CONSTRUCTION_REPORTS", "core:construction_report", "bi bi-bar-chart", 9),
    ],
    "AGRICULTURE": [
        ("Dashboard", "AGRICULTURE_DASHBOARD", "", "bi bi-speedometer2", 1),
        ("Poultry Batches", "AGRICULTURE_POULTRY_BATCHES", "", "bi bi-egg", 2),
        ("Egg Production", "AGRICULTURE_EGG_PRODUCTION", "", "bi bi-basket", 3),
        ("Mortality", "AGRICULTURE_MORTALITY", "", "bi bi-heart-pulse", 4),
    ],
    "MARKETPLACE": [
        ("Dashboard", "MARKETPLACE_DASHBOARD", "ecommerce:shop", "bi bi-speedometer2", 1),
        ("Shop", "MARKETPLACE_SHOP", "ecommerce:shop", "bi bi-shop", 2),
        ("Online Products", "MARKETPLACE_PRODUCTS", "ecommerce:online_product_list", "bi bi-tags", 3),
        ("Online Orders", "MARKETPLACE_ORDERS", "", "bi bi-cart-check", 4),
        ("Sellers", "MARKETPLACE_SELLERS", "ecommerce:marketplace_seller_list", "bi bi-people", 5),
        ("Commissions", "MARKETPLACE_COMMISSIONS", "ecommerce:marketplace_seller_list", "bi bi-percent", 6),
        ("Settlements", "MARKETPLACE_SETTLEMENTS", "ecommerce:seller_settlement_list", "bi bi-wallet2", 7),
        ("Payments", "MARKETPLACE_PAYMENTS", "ecommerce:payment_list", "bi bi-credit-card", 8),
        ("Reports", "MARKETPLACE_REPORTS", "ecommerce:marketplace_report", "bi bi-graph-up", 9),
    ],
}


ENGINE_FEATURES = {
    "CUSTOMER": [
        ("Customers", "CUSTOMER_LIST", "sales:customer_list", "bi bi-people", 1),
        ("Customer History", "CUSTOMER_HISTORY", "sales:customer_list", "bi bi-clock-history", 2),
    ],
    "ORDER": [
        ("All Orders", "ORDER_LIST", "orders:order_list", "bi bi-list-ul", 1),
        ("Restock Orders", "ORDER_RESTOCK", "orders:business_unit_select", "bi bi-arrow-repeat", 2),
        ("Order Approval", "ORDER_APPROVAL", "orders:order_list", "bi bi-check-circle", 3),
        ("Order Fulfilment", "ORDER_FULFILMENT", "orders:order_list", "bi bi-truck", 4),
        ("Sales Dashboard", "SALES_DASHBOARD", "sales:sales_dashboard", "bi bi-speedometer2", 5),
        ("Sales", "SALES_LIST", "sales:sale_list", "bi bi-receipt", 6),
        ("Invoices", "SALES_INVOICES", "sales:invoice_list", "bi bi-file-earmark-text", 7),
        ("Customer Payments", "SALES_PAYMENTS", "sales:payment_list", "bi bi-cash-coin", 8),
        ("Sales Reports", "SALES_REPORTS", "sales:sales_report", "bi bi-bar-chart", 9),
    ],
    "QUOTATION": [
        ("Quotations", "QUOTATION_LIST", "sales:quotation_list", "bi bi-file-earmark-text", 1),
        ("Quotation Approval", "QUOTATION_APPROVAL", "sales:quotation_list", "bi bi-check-circle", 2),
    ],
    "INVENTORY": [
        ("Dashboard", "INVENTORY_DASHBOARD", "inventory:inventory_dashboard", "bi bi-speedometer2", 1),
        ("Products", "INVENTORY_PRODUCTS", "inventory:product_list", "bi bi-box", 2),
        ("Raw Materials", "INVENTORY_RAW_MATERIALS", "inventory:rawmaterial_list", "bi bi-boxes", 3),
        ("Stock Movements", "INVENTORY_STOCK_MOVEMENTS", "inventory:movement_list", "bi bi-arrow-left-right", 4),
        ("Reports", "INVENTORY_REPORTS", "core:inventory_report", "bi bi-bar-chart", 5),
    ],
    "FINANCE": [
        ("Dashboard", "FINANCE_DASHBOARD", "finance:finance_dashboard", "bi bi-speedometer2", 1),
        ("Accounts", "FINANCE_ACCOUNTS", "finance:account_list", "bi bi-bank", 2),
        ("Income", "FINANCE_INCOME", "finance:income_list", "bi bi-arrow-down-circle", 3),
        ("Business Unit Income", "FINANCE_INCOME_DECLARATIONS", "finance:income_declaration_list", "bi bi-cash-stack", 4),
        ("Income Confirmations", "FINANCE_INCOME_CONFIRMATIONS", "finance:income_declaration_list", "bi bi-patch-check", 5),
        ("Expenses", "FINANCE_EXPENSES", "finance:expense_list", "bi bi-arrow-up-circle", 6),
        ("Expense Requests", "FINANCE_EXPENSE_REQUESTS", "finance:expense_request_list", "bi bi-send-check", 7),
        ("Approval Queue", "FINANCE_EXPENSE_APPROVALS", "finance:expense_request_list", "bi bi-check2-square", 8),
        ("Payments", "FINANCE_PAYMENTS", "finance:payment_list", "bi bi-cash", 9),
        ("Receivables", "FINANCE_RECEIVABLES", "finance:receivable_list", "bi bi-wallet2", 8),
        ("Payables", "FINANCE_PAYABLES", "finance:payable_list", "bi bi-receipt", 9),
        ("People & Companies", "FINANCE_COUNTERPARTIES", "finance:counterparty_phone_lookup", "bi bi-person-vcard", 10),
        ("Debts", "FINANCE_DEBTS", "finance:debt_list", "bi bi-journal-text", 11),
        ("Payroll", "FINANCE_PAYROLL", "finance:payroll_list", "bi bi-people", 12),
        ("Financial Reports", "FINANCE_REPORTS", "finance:financial_report", "bi bi-bar-chart", 13),
    ],
    "PEOPLE": [
        ("Dashboard", "PEOPLE_DASHBOARD", "employee:employee_dashboard", "bi bi-speedometer2", 1),
        ("Employees", "PEOPLE_EMPLOYEES", "employee:employee_list", "bi bi-person-badge", 2),
        ("Departments", "PEOPLE_DEPARTMENTS", "employee:department_list", "bi bi-diagram-3", 3),
        ("Attendance", "PEOPLE_ATTENDANCE", "employee:attendance_list", "bi bi-calendar-check", 4),
        ("Leave", "PEOPLE_LEAVE", "employee:leave_list", "bi bi-calendar-x", 5),
        ("Positions", "PEOPLE_POSITIONS", "employee:position_list", "bi bi-person-workspace", 6),
        ("Contacts", "PEOPLE_CONTACTS", "employee:contact_list", "bi bi-person-lines-fill", 7),
        ("People Reports", "PEOPLE_REPORTS", "employee:employee_report", "bi bi-file-bar-graph", 8),
    ],
    "ASSET": [
        ("Assets", "ASSET_LIST", "", "bi bi-tools", 1),
        ("Asset Assignments", "ASSET_ASSIGNMENTS", "", "bi bi-person-check", 2),
    ],
    "APPROVAL": [
        ("Pending Approvals", "APPROVAL_PENDING", "", "bi bi-hourglass-split", 1),
        ("Approval History", "APPROVAL_HISTORY", "", "bi bi-clock-history", 2),
    ],
    "NOTIFICATION": [
        ("Notifications", "NOTIFICATION_LIST", "", "bi bi-bell", 1),
    ],
    "AUDIT": [
        ("Audit Logs", "AUDIT_LOGS", "", "bi bi-shield-check", 1),
        ("Audit Logs", "AUDIT_LOGS", "core:audit_log_list", "bi bi-shield-check", 1),
    ],
    "REPORTING": [
        ("Executive Dashboard", "REPORTING_EXECUTIVE_DASHBOARD", "core:dashboard", "bi bi-graph-up", 1),
        ("Reports", "REPORTING_REPORTS", "", "bi bi-file-bar-graph", 2),
    ],
}


# ======================================================
# DASHBOARD CARDS
# Temporary legacy cards while Reporting Engine is being improved.
# ======================================================

DASHBOARD_CARDS = {
    "FURNITURE": [
        ("Production Jobs", "FURNITURE_JOBS", "bi bi-list-task", "primary", 1),
        ("Completed Outputs", "FURNITURE_OUTPUT_COUNT", "bi bi-box-arrow-up", "success", 2),
    ],
    "CONSTRUCTION": [
        ("Active Projects", "CONSTRUCTION_ACTIVE_PROJECTS", "bi bi-building", "primary", 1),
        ("Delayed Projects", "CONSTRUCTION_DELAYED_PROJECTS", "bi bi-exclamation-triangle", "danger", 2),
    ],
    "AGRICULTURE": [
        ("Egg Production", "AGRICULTURE_EGG_PRODUCTION_CARD", "bi bi-basket", "success", 1),
        ("Mortality", "AGRICULTURE_MORTALITY_CARD", "bi bi-heart-pulse", "danger", 2),
    ],
    "MARKETPLACE": [
        ("Online Orders", "MARKETPLACE_ONLINE_ORDERS", "bi bi-cart-check", "primary", 1),
        ("Online Products", "MARKETPLACE_ONLINE_PRODUCTS", "bi bi-tags", "success", 2),
    ],
    "INVENTORY": [
        ("Products", "INVENTORY_PRODUCTS_COUNT", "bi bi-box", "primary", 1),
        ("Raw Materials", "INVENTORY_RAW_MATERIALS_COUNT", "bi bi-boxes", "success", 2),
    ],
    "FINANCE": [
        ("Total Income", "FINANCE_TOTAL_INCOME", "bi bi-arrow-down-circle", "success", 1),
        ("Total Expenses", "FINANCE_TOTAL_EXPENSE", "bi bi-arrow-up-circle", "danger", 2),
        ("Net Profit", "FINANCE_NET_PROFIT", "bi bi-graph-up", "primary", 3),
    ],
    "PEOPLE": [
        ("Employees", "PEOPLE_EMPLOYEE_COUNT", "bi bi-people", "info", 1),
        ("Attendance", "PEOPLE_ATTENDANCE_COUNT", "bi bi-calendar-check", "primary", 2),
    ],
}


# ======================================================
# KPI WIDGETS
# New enterprise dashboard widgets
# ======================================================

KPI_WIDGETS = {
    "business_units": {
        "FURNITURE": [
            ("Active Production Jobs", "FURNITURE_ACTIVE_JOBS", "NUMBER", "furniture.active_jobs", "value", "bi bi-list-task", "primary", 1),
            ("Completed Outputs", "FURNITURE_COMPLETED_OUTPUTS", "NUMBER", "furniture.completed_outputs", "value", "bi bi-box-arrow-up", "success", 2),
            ("Material Usage", "FURNITURE_MATERIAL_USAGE", "MONEY", "furniture.material_usage", "value", "bi bi-tree", "warning", 3),
        ],

        "CONSTRUCTION": [
            ("Active Projects", "CONSTRUCTION_ACTIVE_PROJECTS_KPI", "NUMBER", "construction.active_projects", "value", "bi bi-building", "primary", 1),
            ("Delayed Projects", "CONSTRUCTION_DELAYED_PROJECTS_KPI", "NUMBER", "construction.delayed_projects", "value", "bi bi-exclamation-triangle", "danger", 2),
            ("Project Budget Used", "CONSTRUCTION_BUDGET_USED", "MONEY", "construction.budget_used", "value", "bi bi-cash-stack", "success", 3),
        ],

        "AGRICULTURE": [
            ("Egg Production", "AGRICULTURE_EGG_PRODUCTION_KPI", "NUMBER", "agriculture.egg_production", "value", "bi bi-basket", "success", 1),
            ("Chicken Mortality", "AGRICULTURE_MORTALITY_KPI", "NUMBER", "agriculture.mortality", "value", "bi bi-heart-pulse", "danger", 2),
        ],

        "MARKETPLACE": [
            ("Online Orders", "MARKETPLACE_ONLINE_ORDERS_KPI", "NUMBER", "marketplace.online_orders", "value", "bi bi-cart-check", "primary", 1),
            ("Online Products", "MARKETPLACE_ONLINE_PRODUCTS_KPI", "NUMBER", "marketplace.online_products", "value", "bi bi-tags", "success", 2),
        ],
    },

    "engines": {
        "FINANCE": [
            ("Total Income", "FINANCE_TOTAL_INCOME_KPI", "MONEY", "finance.total_income", "value", "bi bi-arrow-down-circle", "success", 1),
            ("Total Expenses", "FINANCE_TOTAL_EXPENSE_KPI", "MONEY", "finance.total_expense", "value", "bi bi-arrow-up-circle", "danger", 2),
            ("Net Profit", "FINANCE_NET_PROFIT_KPI", "MONEY", "finance.net_profit", "value", "bi bi-graph-up", "primary", 3),
        ],

        "INVENTORY": [
            ("Products", "INVENTORY_PRODUCTS_KPI", "NUMBER", "inventory.products", "value", "bi bi-box", "primary", 1),
            ("Raw Materials", "INVENTORY_RAW_MATERIALS_KPI", "NUMBER", "inventory.raw_materials", "value", "bi bi-boxes", "success", 2),
            ("Stock Alerts", "INVENTORY_STOCK_ALERTS_KPI", "ALERT", "inventory.stock_alerts", "value", "bi bi-exclamation-circle", "danger", 3),
        ],

        "ORDER": [
            ("Total Orders", "ORDER_TOTAL_KPI", "NUMBER", "orders.total_orders", "value", "bi bi-cart-check", "primary", 1),
            ("Pending Orders", "ORDER_PENDING_KPI", "NUMBER", "orders.pending_orders", "value", "bi bi-clock", "warning", 2),
        ],

        "PEOPLE": [
            ("Employees", "PEOPLE_EMPLOYEES_KPI", "NUMBER", "people.employees", "value", "bi bi-people", "info", 1),
            ("Attendance Today", "PEOPLE_ATTENDANCE_TODAY_KPI", "NUMBER", "people.attendance_today", "value", "bi bi-calendar-check", "primary", 2),
        ],
    },
}
# ======================================================
# DEFAULT GROUPS
# ======================================================

GROUPS = [
    "CEO",
    "Administrator",
    "Manager",

    "Construction Manager",
    "Construction Supervisor",
    "Construction Worker",

    "Furniture Manager",
    "Production Supervisor",
    "Carpentry Supervisor",
    "Carpentry Worker",
    "Machinist Supervisor",
    "Machinist Worker",

    "Finance Manager",
    "Accountant",

    "Inventory Manager",
    "Store Keeper",

    "HR Manager",
    "Sales Officer",
    "Marketplace Manager",

    "Worker",
    "Customer",
]


# ======================================================
# ROLE FEATURE PERMISSIONS
# ======================================================

ROLE_FEATURES = {
    "CEO": {
        "ALL": {"view": True, "add": True, "edit": True, "delete": True, "approve": True}
    },

    "Administrator": {
        "ALL": {"view": True, "add": True, "edit": True, "delete": True, "approve": True}
    },

    "Manager": {
        "ALL": {"view": True, "add": False, "edit": False, "delete": False, "approve": False}
        ,"FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True}
        ,"FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True}
        ,"FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True}
        ,"FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True}
    },

    "Construction Manager": {
        "CONSTRUCTION_DASHBOARD": {"view": True},
        "CONSTRUCTION_PROJECTS": {"view": True, "add": True, "edit": True, "approve": True},
        "CONSTRUCTION_SITES": {"view": True, "add": True, "edit": True},
        "CONSTRUCTION_TASKS": {"view": True, "add": True, "edit": True},
        "INVENTORY_DASHBOARD": {"view": True},
        "INVENTORY_RAW_MATERIALS": {"view": True},
        "FINANCE_DASHBOARD": {"view": True},
        "FINANCE_EXPENSES": {"view": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True},
        "CUSTOMER_LIST": {"view": True},
    },

    "Construction Supervisor": {
        "CONSTRUCTION_DASHBOARD": {"view": True},
        "CONSTRUCTION_PROJECTS": {"view": True, "edit": True},
        "CONSTRUCTION_SITES": {"view": True, "edit": True},
        "CONSTRUCTION_TASKS": {"view": True, "add": True, "edit": True},
        "INVENTORY_RAW_MATERIALS": {"view": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Construction Worker": {
        "CONSTRUCTION_DASHBOARD": {"view": True},
        "CONSTRUCTION_TASKS": {"view": True, "edit": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Furniture Manager": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "add": True, "edit": True, "approve": True},
        "FURNITURE_QUOTATIONS": {"view": True, "add": True, "edit": True, "approve": True},
        "FURNITURE_MATERIALS": {"view": True, "add": True, "edit": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True},
        "INVENTORY_DASHBOARD": {"view": True},
        "INVENTORY_PRODUCTS": {"view": True},
        "INVENTORY_RAW_MATERIALS": {"view": True},
        "INVENTORY_STOCK_MOVEMENTS": {"view": True, "add": True},
        "ORDER_LIST": {"view": True, "add": True, "edit": True},
        "ORDER_RESTOCK": {"view": True, "add": True},
        "QUOTATION_LIST": {"view": True},
    },

    "Production Supervisor": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "add": True, "edit": True},
        "FURNITURE_MATERIALS": {"view": True, "add": True, "edit": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True, "edit": True},
        "INVENTORY_RAW_MATERIALS": {"view": True},
        "INVENTORY_STOCK_MOVEMENTS": {"view": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Carpentry Supervisor": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "edit": True},
        "FURNITURE_MATERIALS": {"view": True, "add": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Carpentry Worker": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "edit": True},
        "FURNITURE_MATERIALS": {"view": True, "add": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Machinist Supervisor": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "edit": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True},
        "ASSET_LIST": {"view": True},
        "ASSET_ASSIGNMENTS": {"view": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Machinist Worker": {
        "FURNITURE_DASHBOARD": {"view": True},
        "FURNITURE_PRODUCTION_JOBS": {"view": True, "edit": True},
        "FURNITURE_OUTPUTS": {"view": True, "add": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
    },

    "Finance Manager": {
        "FINANCE_DASHBOARD": {"view": True},
        "FINANCE_ACCOUNTS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME": {"view": True, "add": True, "edit": True, "approve": True},
        "FINANCE_EXPENSES": {"view": True, "add": True, "edit": True, "approve": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True},
        "FINANCE_PAYMENTS": {"view": True, "add": True, "edit": True, "approve": True},
        "FINANCE_RECEIVABLES": {"view": True, "add": True, "edit": True},
        "FINANCE_PAYABLES": {"view": True, "add": True, "edit": True},
        "FINANCE_COUNTERPARTIES": {"view": True, "add": True, "edit": True, "delete": True},
        "FINANCE_DEBTS": {"view": True, "add": True, "edit": True, "delete": True},
        "REPORTING_EXECUTIVE_DASHBOARD": {"view": True},
        "ORDER_LIST": {"view": True},
        "CUSTOMER_LIST": {"view": True},
    },

    "Accountant": {
        "FINANCE_DASHBOARD": {"view": True},
        "FINANCE_ACCOUNTS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSES": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True},
        "FINANCE_PAYMENTS": {"view": True, "add": True, "edit": True},
        "FINANCE_RECEIVABLES": {"view": True, "add": True, "edit": True},
        "FINANCE_PAYABLES": {"view": True, "add": True, "edit": True},
    },

    "Inventory Manager": {
        "INVENTORY_DASHBOARD": {"view": True},
        "INVENTORY_PRODUCTS": {"view": True, "add": True, "edit": True},
        "INVENTORY_RAW_MATERIALS": {"view": True, "add": True, "edit": True},
        "INVENTORY_STOCK_MOVEMENTS": {"view": True, "add": True, "edit": True, "approve": True},
        "ASSET_LIST": {"view": True, "add": True, "edit": True},
        "ASSET_ASSIGNMENTS": {"view": True, "add": True, "edit": True},
    },

    "Store Keeper": {
        "INVENTORY_DASHBOARD": {"view": True},
        "INVENTORY_PRODUCTS": {"view": True},
        "INVENTORY_RAW_MATERIALS": {"view": True},
        "INVENTORY_STOCK_MOVEMENTS": {"view": True, "add": True},
        "ASSET_LIST": {"view": True},
    },

    "HR Manager": {
        "PEOPLE_DASHBOARD": {"view": True},
        "PEOPLE_EMPLOYEES": {"view": True, "add": True, "edit": True},
        "PEOPLE_DEPARTMENTS": {"view": True, "add": True, "edit": True},
        "PEOPLE_ATTENDANCE": {"view": True, "add": True, "edit": True},
        "PEOPLE_LEAVE": {"view": True, "add": True, "edit": True, "approve": True},
    },

    "Sales Officer": {
        "CUSTOMER_LIST": {"view": True, "add": True, "edit": True},
        "CUSTOMER_HISTORY": {"view": True},
        "ORDER_LIST": {"view": True, "add": True, "edit": True},
        "MARKETPLACE_SHOP": {"view": True},
        "MARKETPLACE_PRODUCTS": {"view": True},
        "MARKETPLACE_ORDERS": {"view": True, "add": True, "edit": True},
    },

    "Marketplace Manager": {
        "MARKETPLACE_DASHBOARD": {"view": True},
        "MARKETPLACE_SHOP": {"view": True, "add": True, "edit": True},
        "MARKETPLACE_PRODUCTS": {"view": True, "add": True, "edit": True},
        "MARKETPLACE_ORDERS": {"view": True, "edit": True},
        "ORDER_LIST": {"view": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True, "edit": True},
        "FINANCE_EXPENSE_APPROVALS": {"view": True, "edit": True, "approve": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True, "edit": True},
        "FINANCE_INCOME_CONFIRMATIONS": {"view": True, "edit": True, "approve": True},
        "CUSTOMER_LIST": {"view": True},
    },

    "Worker": {
        "PEOPLE_ATTENDANCE": {"view": True, "add": True},
        "FINANCE_EXPENSE_REQUESTS": {"view": True, "add": True},
        "FINANCE_INCOME_DECLARATIONS": {"view": True, "add": True},
    },

    "Customer": {
        "MARKETPLACE_SHOP": {"view": True},
        "MARKETPLACE_PRODUCTS": {"view": True},
        "MARKETPLACE_ORDERS": {"view": True, "add": True},
    },
}


GROUP_LANDING_FEATURES = {
    "Finance Manager": "FINANCE_DASHBOARD",
    "Accountant": "FINANCE_DASHBOARD",
    "Inventory Manager": "INVENTORY_DASHBOARD",
    "Store Keeper": "INVENTORY_DASHBOARD",
    "HR Manager": "PEOPLE_DASHBOARD",
    "Sales Officer": "SALES_DASHBOARD",
    "Marketplace Manager": "MARKETPLACE_DASHBOARD",
    "Construction Manager": "CONSTRUCTION_DASHBOARD",
    "Construction Supervisor": "CONSTRUCTION_DASHBOARD",
    "Construction Worker": "CONSTRUCTION_DASHBOARD",
    "Furniture Manager": "FURNITURE_DASHBOARD",
    "Production Supervisor": "FURNITURE_DASHBOARD",
    "Carpentry Supervisor": "FURNITURE_DASHBOARD",
    "Carpentry Worker": "FURNITURE_DASHBOARD",
    "Machinist Supervisor": "FURNITURE_DASHBOARD",
    "Machinist Worker": "FURNITURE_DASHBOARD",
    "Customer": "MARKETPLACE_SHOP",
}


# Django permissions are the authorization source of truth. Feature records
# store these names so newly created Groups can gain access from Django Admin
# without adding their names to application code.
FEATURE_DJANGO_PERMISSIONS = {
    "MARKETPLACE_DASHBOARD": {"view_permission": "ecommerce.view_onlineproduct"},
    "MARKETPLACE_PRODUCTS": {"view_permission": "ecommerce.view_onlineproduct", "add_permission": "ecommerce.add_onlineproduct", "change_permission": "ecommerce.change_onlineproduct", "delete_permission": "ecommerce.delete_onlineproduct"},
    "MARKETPLACE_ORDERS": {"view_permission": "ecommerce.view_ecommercecheckout", "add_permission": "ecommerce.add_ecommercecheckout", "change_permission": "ecommerce.change_ecommercecheckout", "delete_permission": "ecommerce.delete_ecommercecheckout"},
    "MARKETPLACE_SELLERS": {"view_permission": "ecommerce.view_marketplaceseller", "add_permission": "ecommerce.add_marketplaceseller", "change_permission": "ecommerce.change_marketplaceseller", "delete_permission": "ecommerce.delete_marketplaceseller"},
    "MARKETPLACE_COMMISSIONS": {"view_permission": "ecommerce.view_sellerproductassignment", "add_permission": "ecommerce.add_sellerproductassignment", "change_permission": "ecommerce.change_sellerproductassignment", "delete_permission": "ecommerce.delete_sellerproductassignment"},
    "MARKETPLACE_SETTLEMENTS": {"view_permission": "ecommerce.view_sellersettlement", "add_permission": "ecommerce.add_sellersettlement", "change_permission": "ecommerce.change_sellersettlement", "delete_permission": "ecommerce.delete_sellersettlement", "approve_permission": "ecommerce.approve_sellersettlement"},
    "MARKETPLACE_PAYMENTS": {"view_permission": "ecommerce.view_ecommercepayment", "add_permission": "ecommerce.add_ecommercepayment", "change_permission": "ecommerce.change_ecommercepayment", "delete_permission": "ecommerce.delete_ecommercepayment", "approve_permission": "ecommerce.confirm_ecommercepayment"},
    "MARKETPLACE_REPORTS": {"view_permission": "ecommerce.view_marketplaceorderline"},
    "MARKETPLACE_PAYMENT_CONFIRM": {"approve_permission": "ecommerce.confirm_ecommercepayment"},
    "MARKETPLACE_PAYMENT_REFUND": {"approve_permission": "ecommerce.refund_ecommercepayment"},
    "MARKETPLACE_SETTLEMENT_PAY": {"approve_permission": "ecommerce.pay_sellersettlement"},
    "FURNITURE_DASHBOARD": {"view_permission": "furniture.view_productionjob"},
    "FURNITURE_PRODUCTION_JOBS": {"view_permission": "furniture.view_productionjob", "add_permission": "furniture.add_productionjob", "change_permission": "furniture.change_productionjob", "delete_permission": "furniture.delete_productionjob"},
    "FURNITURE_QUOTATIONS": {"view_permission": "furniture.view_quotation", "add_permission": "furniture.add_quotation", "change_permission": "furniture.change_quotation", "delete_permission": "furniture.delete_quotation", "approve_permission": "furniture.approve_quotation"},
    "FURNITURE_MATERIALS": {"view_permission": "furniture.view_productionmaterial", "add_permission": "furniture.add_productionmaterial", "change_permission": "furniture.change_productionmaterial", "delete_permission": "furniture.delete_productionmaterial"},
    "FURNITURE_OUTPUTS": {"view_permission": "furniture.view_productionoutput", "add_permission": "furniture.add_productionoutput", "change_permission": "furniture.change_productionoutput", "delete_permission": "furniture.delete_productionoutput"},
    "FURNITURE_ORDERS": {"view_permission": "furniture.view_order", "add_permission": "furniture.add_order", "change_permission": "furniture.change_order", "delete_permission": "furniture.delete_order"},
    "FURNITURE_TASKS": {"view_permission": "furniture.view_productiontask", "add_permission": "furniture.add_productiontask", "change_permission": "furniture.change_productiontask", "delete_permission": "furniture.delete_productiontask"},
    "FURNITURE_MY_TASKS": {"view_permission": "furniture.view_productiontask"},
    "FURNITURE_LABOUR": {"view_permission": "furniture.view_productionlabour", "add_permission": "furniture.add_productionlabour", "change_permission": "furniture.change_productionlabour", "delete_permission": "furniture.delete_productionlabour"},
    "FURNITURE_MACHINES": {"view_permission": "furniture.view_productionmachine", "add_permission": "furniture.add_productionmachine", "change_permission": "furniture.change_productionmachine", "delete_permission": "furniture.delete_productionmachine"},
    "FURNITURE_QUALITY": {"view_permission": "furniture.view_qualityinspection", "add_permission": "furniture.add_qualityinspection", "change_permission": "furniture.change_qualityinspection", "delete_permission": "furniture.delete_qualityinspection", "approve_permission": "furniture.approve_qualityinspection"},
    "FURNITURE_REWORK": {"view_permission": "furniture.view_reworkorder", "add_permission": "furniture.add_reworkorder", "change_permission": "furniture.change_reworkorder", "delete_permission": "furniture.delete_reworkorder", "approve_permission": "furniture.verify_reworkorder"},
    "FURNITURE_REPORTS": {"view_permission": "furniture.view_productionjob"},
    "FURNITURE_SETTINGS": {"view_permission": "furniture.view_productionsettings", "change_permission": "furniture.change_productionsettings"},
    "CUSTOMER_LIST": {
        "view_permission": "sales.view_customer",
        "add_permission": "sales.add_customer",
        "change_permission": "sales.change_customer",
        "delete_permission": "sales.delete_customer",
    },
    "CUSTOMER_HISTORY": {
        "view_permission": "sales.view_customer",
    },
    "QUOTATION_LIST": {
        "view_permission": "sales.view_salesquotation",
        "add_permission": "sales.add_salesquotation",
        "change_permission": "sales.change_salesquotation",
        "delete_permission": "sales.delete_salesquotation",
    },
    "QUOTATION_APPROVAL": {
        "view_permission": "sales.view_salesquotation",
        "approve_permission": "sales.approve_salesquotation",
    },
    "ORDER_LIST": {
        "view_permission": "orders.view_order",
        "add_permission": "orders.add_order",
        "change_permission": "orders.change_order",
        "delete_permission": "orders.delete_order",
    },
    "ORDER_RESTOCK": {
        "view_permission": "orders.view_order",
        "add_permission": "orders.add_order",
    },
    "ORDER_APPROVAL": {
        "view_permission": "orders.view_order",
        "approve_permission": "orders.approve_order",
    },
    "ORDER_FULFILMENT": {
        "view_permission": "orders.view_order",
        "approve_permission": "orders.fulfil_order",
    },
    "SALES_DASHBOARD": {
        "view_permission": "sales.view_sale",
    },
    "SALES_LIST": {
        "view_permission": "sales.view_sale",
        "add_permission": "sales.add_sale",
        "change_permission": "sales.change_sale",
        "delete_permission": "sales.delete_sale",
    },
    "SALES_INVOICES": {
        "view_permission": "sales.view_invoice",
        "add_permission": "sales.add_invoice",
        "change_permission": "sales.change_invoice",
        "delete_permission": "sales.delete_invoice",
    },
    "SALES_PAYMENTS": {
        "view_permission": "sales.view_customerpayment",
        "add_permission": "sales.add_customerpayment",
        "change_permission": "sales.change_customerpayment",
        "delete_permission": "sales.delete_customerpayment",
    },
    "SALES_REPORTS": {
        "view_permission": "sales.view_sale",
    },
    "FINANCE_DASHBOARD": {
        "view_permission": "finance.view_account",
    },
    "FINANCE_ACCOUNTS": {
        "view_permission": "finance.view_account",
        "add_permission": "finance.add_account",
        "change_permission": "finance.change_account",
        "delete_permission": "finance.delete_account",
    },
    "FINANCE_INCOME": {
        "view_permission": "finance.view_income",
        "add_permission": "finance.add_income",
        "change_permission": "finance.change_income",
        "delete_permission": "finance.delete_income",
    },
    "FINANCE_INCOME_DECLARATIONS": {
        "view_permission": "finance.view_incomedeclaration",
        "add_permission": "finance.add_incomedeclaration",
        "change_permission": "finance.change_incomedeclaration",
        "delete_permission": "finance.delete_incomedeclaration",
    },
    "FINANCE_INCOME_CONFIRMATIONS": {
        "view_permission": "finance.view_incomedeclaration",
        "change_permission": "finance.change_incomedeclaration",
        "approve_permission": "finance.change_incomedeclaration",
    },
    "FINANCE_EXPENSES": {
        "view_permission": "finance.view_expense",
        "add_permission": "finance.add_expense",
        "change_permission": "finance.change_expense",
        "delete_permission": "finance.delete_expense",
    },
    "FINANCE_EXPENSE_REQUESTS": {
        "view_permission": "finance.view_expenserequest",
        "add_permission": "finance.add_expenserequest",
        "change_permission": "finance.change_expenserequest",
        "delete_permission": "finance.delete_expenserequest",
    },
    "FINANCE_EXPENSE_APPROVALS": {
        "view_permission": "finance.view_expenserequest",
        "change_permission": "finance.change_expenserequest",
        "approve_permission": "finance.change_expenserequest",
    },
    "FINANCE_PAYMENTS": {
        "view_permission": "finance.view_payment",
        "add_permission": "finance.add_payment",
        "change_permission": "finance.change_payment",
        "delete_permission": "finance.delete_payment",
    },
    "FINANCE_RECEIVABLES": {
        "view_permission": "finance.view_receivable",
        "add_permission": "finance.add_receivable",
        "change_permission": "finance.change_receivable",
        "delete_permission": "finance.delete_receivable",
    },
    "FINANCE_PAYABLES": {
        "view_permission": "finance.view_payable",
        "add_permission": "finance.add_payable",
        "change_permission": "finance.change_payable",
        "delete_permission": "finance.delete_payable",
    },
    "FINANCE_COUNTERPARTIES": {
        "view_permission": "finance.view_counterparty",
        "add_permission": "finance.add_counterparty",
        "change_permission": "finance.change_counterparty",
        "delete_permission": "finance.delete_counterparty",
    },
    "FINANCE_DEBTS": {
        "view_permission": "finance.view_debtrecord",
        "add_permission": "finance.add_debtrecord",
        "change_permission": "finance.change_debtrecord",
        "delete_permission": "finance.delete_debtrecord",
    },
    "FINANCE_PAYROLL": {
        "view_permission": "finance.view_payroll",
        "add_permission": "finance.add_payroll",
        "change_permission": "finance.change_payroll",
        "delete_permission": "finance.delete_payroll",
    },
    "FINANCE_REPORTS": {
        "view_permission": "finance.view_transaction",
    },
    "PEOPLE_DASHBOARD": {
        "view_permission": "Employee.view_employee",
    },
    "PEOPLE_EMPLOYEES": {
        "view_permission": "Employee.view_employee",
        "add_permission": "Employee.add_employee",
        "change_permission": "Employee.change_employee",
        "delete_permission": "Employee.delete_employee",
    },
    "PEOPLE_DEPARTMENTS": {
        "view_permission": "Employee.view_department",
        "add_permission": "Employee.add_department",
        "change_permission": "Employee.change_department",
        "delete_permission": "Employee.delete_department",
    },
    "PEOPLE_ATTENDANCE": {
        "view_permission": "Employee.view_attendance",
        "add_permission": "Employee.add_attendance",
        "change_permission": "Employee.change_attendance",
        "delete_permission": "Employee.delete_attendance",
    },
    "PEOPLE_LEAVE": {
        "view_permission": "Employee.view_leave",
        "add_permission": "Employee.add_leave",
        "change_permission": "Employee.change_leave",
        "delete_permission": "Employee.delete_leave",
    },
    "PEOPLE_POSITIONS": {
        "view_permission": "Employee.view_position",
        "add_permission": "Employee.add_position",
        "change_permission": "Employee.change_position",
        "delete_permission": "Employee.delete_position",
    },
    "PEOPLE_CONTACTS": {
        "view_permission": "Employee.view_contact",
        "add_permission": "Employee.add_contact",
        "change_permission": "Employee.change_contact",
        "delete_permission": "Employee.delete_contact",
    },
    "PEOPLE_REPORTS": {
        "view_permission": "Employee.view_employee",
    },
    "CONSTRUCTION_DASHBOARD": {
        "view_permission": "Construction.view_project",
    },
    "CONSTRUCTION_PROJECTS": {
        "view_permission": "Construction.view_project",
        "add_permission": "Construction.add_project",
        "change_permission": "Construction.change_project",
        "delete_permission": "Construction.delete_project",
    },
    "CONSTRUCTION_SITES": {
        "view_permission": "Construction.view_site",
        "add_permission": "Construction.add_site",
        "change_permission": "Construction.change_site",
        "delete_permission": "Construction.delete_site",
    },
    "CONSTRUCTION_TASKS": {
        "view_permission": "Construction.view_task",
        "add_permission": "Construction.add_task",
        "change_permission": "Construction.change_task",
        "delete_permission": "Construction.delete_task",
    },
    "CONSTRUCTION_MATERIALS": {
        "view_permission": "Construction.view_constructionmaterial",
        "add_permission": "Construction.add_constructionmaterial",
        "change_permission": "Construction.change_constructionmaterial",
        "delete_permission": "Construction.delete_constructionmaterial",
    },
    "CONSTRUCTION_LABOUR": {
        "view_permission": "Construction.view_constructionlabour",
        "add_permission": "Construction.add_constructionlabour",
        "change_permission": "Construction.change_constructionlabour",
        "delete_permission": "Construction.delete_constructionlabour",
    },
    "CONSTRUCTION_ASSET_USAGE": {
        "view_permission": "Construction.view_constructionassetusage",
        "add_permission": "Construction.add_constructionassetusage",
        "change_permission": "Construction.change_constructionassetusage",
        "delete_permission": "Construction.delete_constructionassetusage",
    },
    "CONSTRUCTION_EXPENSES": {
        "view_permission": "Construction.view_constructionexpense",
        "add_permission": "Construction.add_constructionexpense",
        "change_permission": "Construction.change_constructionexpense",
        "delete_permission": "Construction.delete_constructionexpense",
    },
    "CONSTRUCTION_REPORTS": {
        "view_permission": "Construction.view_project",
    },
    "INVENTORY_DASHBOARD": {
        "view_permission": "inventory.view_product",
    },
    "INVENTORY_PRODUCTS": {
        "view_permission": "inventory.view_product",
        "add_permission": "inventory.add_product",
        "change_permission": "inventory.change_product",
        "delete_permission": "inventory.delete_product",
    },
    "INVENTORY_RAW_MATERIALS": {
        "view_permission": "inventory.view_rawmaterial",
        "add_permission": "inventory.add_rawmaterial",
        "change_permission": "inventory.change_rawmaterial",
        "delete_permission": "inventory.delete_rawmaterial",
    },
    "INVENTORY_STOCK_MOVEMENTS": {
        "view_permission": "inventory.view_stockmovement",
        "add_permission": "inventory.add_stockmovement",
        "change_permission": "inventory.change_stockmovement",
        "delete_permission": "inventory.delete_stockmovement",
    },
    "INVENTORY_REPORTS": {
        "view_permission": "inventory.view_product",
    },
    "REPORTING_EXECUTIVE_DASHBOARD": {
        "view_permission": "core.view_executivereport",
    },
    "REPORTING_REPORTS": {
        "view_permission": "core.view_reports",
    },
    "ASSET_LIST": {
        "view_permission": "inventory.view_asset",
        "add_permission": "inventory.add_asset",
        "change_permission": "inventory.change_asset",
        "delete_permission": "inventory.delete_asset",
    },
    "ASSET_ASSIGNMENTS": {
        "view_permission": "inventory.view_assetassignment",
        "add_permission": "inventory.add_assetassignment",
        "change_permission": "inventory.change_assetassignment",
        "delete_permission": "inventory.delete_assetassignment",
    },
    "AUDIT_LOGS": {
        "view_permission": "core.view_auditlog",
    },
}
