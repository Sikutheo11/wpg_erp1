from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count
from finance.models import Income, Expense, Receivable, Payable
from inventory.models import RawMaterial, Asset, Product
from furniture.models import Order
from Construction.models import Project
from Employee.models import Employee, Contact, Department, Position
from django.utils import timezone

# Create your views here.
def home(request):
    return render(request, 'core/home.html')

# =========================
# CUSTOMER DASHBOARD
# =========================
@login_required
def customer_dashboard(request):
    return render(request, 'accounts/customer_dashboard.html')

# =========================
# MANAGER DASHBOARD
# =========================
@login_required
def manager_dashboard(request):

    # ================= FINANCE =================
    total_income = Income.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = total_income - total_expenses

    receivables = Receivable.objects.filter(status='unpaid').aggregate(
        balance=Sum(F('total_amount') - F('amount_paid'))
    )['balance'] or 0

    payables = Payable.objects.filter(status='unpaid').aggregate(
        balance=Sum(F('total_amount') - F('amount_paid'))
    )['balance'] or 0


    # ================= INVENTORY =================
    total_asset_items = Asset.objects.count()

    total_asset_value = Asset.objects.aggregate(
        total=Sum('purchase_cost')
    )['total'] or 0

    active_assets = Asset.objects.filter(status='active').count()
    maintenance_assets = Asset.objects.filter(status='maintenance').count()
    inactive_assets = Asset.objects.filter(status='inactive').count()
    disposed_assets = Asset.objects.filter(status='disposed').count()

    total_product_items = Product.objects.count()
    total_product_value = Product.objects.aggregate(
        total=Sum('selling_price')
    )['total'] or 0

    total_raw_material = RawMaterial.objects.count()
    total_raw_material_value = RawMaterial.objects.aggregate(
        total=Sum('unit_cost')
    )['total'] or 0

    low_raw_material = RawMaterial.objects.filter(status='low').count()
    out_of_raw_material = RawMaterial.objects.filter(status='out_of_stock').count()

    # 🔥 FIXED INVENTORY ALERT VALUES
    low_stock = low_raw_material
    out_of_stock = out_of_raw_material


    # ================= ORDERS =================
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='completed').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()


    # ================= PROJECTS =================
    total_projects = Project.objects.count()
    planning_projects = Project.objects.filter(status='planning').count()
    ongoing_projects = Project.objects.filter(status='ongoing').count()
    paused_projects = Project.objects.filter(status='paused').count()
    completed_projects = Project.objects.filter(status='completed').count()
    delayed_projects = Project.objects.filter(end_date__lt=timezone.now().date(),status__in=['active', 'pending']).count()
    cancelled_projects = Project.objects.filter(status='cancelled').count()
    project_budget_used = Project.objects.aggregate(
        total=Sum('budget')
    )['total'] or 0


    # ================= WORKERS =================
    total_workers = Employee.objects.count()
    total_departments = Department.objects.count()

    present_workers = 0
    absent_workers = 0


    # ================= CONTACTS =================
    total_contacts = Contact.objects.count()

    contacts_construction = Contact.objects.filter(department__name="Construction").count()
    contacts_furniture = Contact.objects.filter(department__name="Furniture").count()
    contacts_sales = Contact.objects.filter(department__name="Sales").count()
    contacts_suppliers = Contact.objects.filter(role="supplier").count()


    # ================= ALERTS =================
    alerts = []

    if low_stock > 0:
        alerts.append("⚠️ Some inventory items are low in stock")

    if out_of_stock > 0:
        alerts.append("❌ Some items are out of stock")

    if delayed_projects > 0:
        alerts.append("⏳ Some projects are delayed")

    if payables > 0:
        alerts.append("💰 Company has unpaid supplier bills")


    # ================= CONTEXT =================
    context = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_profit": net_profit,

        "receivables": receivables,
        "payables": payables,

        "total_asset_items": total_asset_items,
        "total_asset_value": total_asset_value,

        "active_assets": active_assets,
        "maintenance_assets": maintenance_assets,
        "inactive_assets": inactive_assets,
        "disposed_assets": disposed_assets,

        "total_product_items": total_product_items,
        "total_product_value": total_product_value,

        "total_raw_material": total_raw_material,
        "total_raw_material_value": total_raw_material_value,

        "low_stock": low_stock,
        "out_of_stock": out_of_stock,

        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,

        "total_projects": total_projects,
        "completed_projects": completed_projects,
        "delayed_projects": delayed_projects,
        "project_budget_used": project_budget_used,
        "paused_projects": paused_projects,
        "cancelled_projects": cancelled_projects,
        "planning_projects": planning_projects,
        "ongoing_projects": ongoing_projects,

        "total_workers": total_workers,
        "total_departments": total_departments,
        "present_workers": present_workers,
        "absent_workers": absent_workers,

        "total_contacts": total_contacts,
        "contacts_construction": contacts_construction,
        "contacts_furniture": contacts_furniture,
        "contacts_sales": contacts_sales,
        "contacts_suppliers": contacts_suppliers,

        "alerts": alerts,
    }

    return render(request, "core/manager_dashboard.html", context)


# =========================
# ADMIN DASHBOARD
# =========================
@login_required
def admin_dashboard(request):

    # Finance
    total_income = Income.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    total_expenses = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    net_profit = total_income - total_expenses

    # Employees
    total_employees = Employee.objects.count()
    active_employees = Employee.objects.filter(
        is_active=True
    ).count()

    total_departments = Department.objects.count()
    total_positions = Position.objects.count()

    # Projects
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(
        status='active'
    ).count()

    completed_projects = Project.objects.filter(
        status='completed'
    ).count()

    # Inventory
    total_assets = Asset.objects.count()

    total_asset_value = Asset.objects.aggregate(
        total=Sum('purchase_cost')
    )['total'] or 0

    total_products = Product.objects.count()

    total_raw_materials = RawMaterial.objects.count()

    # Orders
    total_orders = Order.objects.count()

    pending_orders = Order.objects.filter(
        status='pending'
    ).count()

    completed_orders = Order.objects.filter(
        status='completed'
    ).count()

    context = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_profit': net_profit,

        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_departments': total_departments,
        'total_positions': total_positions,

        'total_projects': total_projects,
        'active_projects': active_projects,
        'completed_projects': completed_projects,

        'total_assets': total_assets,
        'total_asset_value': total_asset_value,
        'total_products': total_products,
        'total_raw_materials': total_raw_materials,

        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }

    return render(request, 'core/admin_dashboard.html', context)


