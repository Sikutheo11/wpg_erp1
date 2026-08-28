from django.db import migrations

FURNITURE_NAVIGATION = {
    "FURNITURE_DASHBOARD": {"name": "Production Overview", "url_name": "furniture:production_job_list", "icon": "bi bi-speedometer2", "order": 1},
    "FURNITURE_PRODUCTION_JOBS": {"name": "Production Jobs", "url_name": "furniture:production_job_list", "icon": "bi bi-list-task", "order": 2},
    "FURNITURE_QUOTATIONS": {"name": "Production Costing", "url_name": "furniture:quotation_list", "icon": "bi bi-calculator", "order": 3},
    "FURNITURE_MATERIALS": {"name": "Materials", "url_name": "furniture:material_list", "icon": "bi bi-tree", "order": 4},
    "FURNITURE_OUTPUTS": {"name": "Outputs", "url_name": "furniture:output_list", "icon": "bi bi-box-arrow-up", "order": 5},
    "FURNITURE_ORDERS": {"name": "Legacy Records (Read Only)", "url_name": "furniture:order_list", "icon": "bi bi-archive", "order": 6},
    "FURNITURE_TASKS": {"name": "Production Tasks", "url_name": "furniture:production_task_list", "icon": "bi bi-check2-square", "order": 7},
    "FURNITURE_MY_TASKS": {"name": "My Tasks", "url_name": "furniture:my_production_tasks", "icon": "bi bi-person-check", "order": 8},
    "FURNITURE_LABOUR": {"name": "Labour", "url_name": "furniture:labour_list", "icon": "bi bi-people", "order": 9},
    "FURNITURE_MACHINES": {"name": "Machines", "url_name": "furniture:machine_list", "icon": "bi bi-gear", "order": 10},
    "FURNITURE_QUALITY": {"name": "Quality", "url_name": "furniture:quality_inspection_list", "icon": "bi bi-shield-check", "order": 11},
    "FURNITURE_REWORK": {"name": "Rework", "url_name": "furniture:rework_order_list", "icon": "bi bi-arrow-repeat", "order": 12},
    "FURNITURE_REPORTS": {"name": "Reports", "url_name": "furniture:production_reports", "icon": "bi bi-bar-chart", "order": 13},
    "FURNITURE_SETTINGS": {"name": "Settings", "url_name": "furniture:production_settings", "icon": "bi bi-sliders", "order": 14},
}

def sync_furniture_navigation(apps, schema_editor):
    Feature = apps.get_model("core", "Feature")
    BusinessUnit = apps.get_model("core", "BusinessUnit")
    furniture = BusinessUnit.objects.filter(code="FURNITURE").first()
    if furniture is None:
        return
    for code, values in FURNITURE_NAVIGATION.items():
        Feature.objects.filter(code=code, business_unit=furniture).update(**values)

class Migration(migrations.Migration):
    dependencies = [
        ("core", "0028_jobfinanceexpenselink_jobfinanceincomelink"),
    ]
    operations = [
        migrations.RunPython(sync_furniture_navigation, migrations.RunPython.noop),
    ]
