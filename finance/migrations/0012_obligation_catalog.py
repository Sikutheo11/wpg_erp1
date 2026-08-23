from django.db import migrations, models
import django.db.models.deletion


CATALOG = {
    "FURNITURE": {
        "Furniture Products": ["Dining Chair", "Office Chair", "School Desk", "Dining Table", "Office Table", "Bed", "Sofa", "Cabinet", "Wardrobe", "Bookshelf", "Door", "Window"],
        "Timber & Boards": ["Timber", "Plywood", "MDF Board", "Blockboard", "Hardboard", "Veneer"],
        "Metal Materials": ["Steel Tube", "Angle Bar", "Flat Bar", "Metal Sheet", "Welding Rod"],
        "Upholstery Materials": ["Foam", "Fabric", "Leather", "Mattress Material", "Thread"],
        "Finishing Materials": ["Paint", "Varnish", "Wood Stain", "Sandpaper", "Thinner", "Glue"],
        "Furniture Hardware": ["Nails", "Screws", "Hinges", "Locks", "Handles", "Drawer Slides"],
        "Labour & Services": ["Carpenter", "Welder", "Upholsterer", "Painter", "Designer", "Installer", "Casual Worker"],
        "Machines & Tools": ["Circular Saw", "Planer", "Sander", "Welding Machine", "Drill", "Hand Tool"],
        "Operations & Overheads": ["Transport", "Machine Repair", "Machine Rental", "Workshop Rent", "Electricity", "Water", "Tax", "Insurance"],
    },
    "CONSTRUCTION": {
        "Construction Works": ["New Building", "Renovation", "Masonry", "Roofing", "Plastering", "Flooring", "Painting"],
        "Building Materials": ["Cement", "Sand", "Aggregate", "Bricks", "Blocks", "Stone", "Lime"],
        "Reinforcement & Metal": ["Reinforcement Bar", "Binding Wire", "Steel Tube", "Metal Sheet"],
        "Roofing Materials": ["Roofing Sheet", "Timber", "Gutter", "Roofing Nails", "Ceiling Material"],
        "Plumbing Materials": ["Water Pipe", "Pipe Fitting", "Water Tank", "Tap", "Sanitary Equipment"],
        "Electrical Materials": ["Electric Cable", "Socket", "Switch", "Breaker", "Light", "Distribution Board"],
        "Doors & Windows": ["Wooden Door", "Metal Door", "Aluminium Window", "Glass", "Door Lock"],
        "Labour & Services": ["Mason", "Carpenter", "Welder", "Electrician", "Plumber", "Painter", "Engineer", "Site Supervisor", "Casual Worker"],
        "Equipment & Tools": ["Concrete Mixer", "Compactor", "Scaffolding", "Wheelbarrow", "Ladder", "Power Tool"],
        "Project Overheads": ["Transport", "Equipment Rental", "Equipment Repair", "Site Security", "Permit", "Electricity", "Water", "Tax", "Insurance"],
    },
    "AGRICULTURE": {
        "Poultry Birds": ["Day-old Chick", "Broiler", "Layer", "Breeder Hen", "Breeder Cock", "Grower", "Culled Bird"],
        "Eggs & Poultry Products": ["Table Egg", "Hatching Egg", "Tray of Eggs", "Chicken Meat", "Manure"],
        "Poultry Feed": ["Chick Starter", "Broiler Starter", "Broiler Finisher", "Layer Mash", "Grower Mash", "Breeder Feed"],
        "Feed Ingredients": ["Maize", "Soybean Meal", "Fish Meal", "Bran", "Premix", "Limestone", "Salt"],
        "Health & Biosecurity": ["Vaccine", "Medicine", "Vitamin", "Disinfectant", "Footbath Chemical", "Veterinary Service"],
        "Poultry Supplies": ["Feeder", "Drinker", "Egg Tray", "Litter", "Gas", "Packaging Material"],
        "Incubation & Brooding": ["Incubation Service", "Chick Hatching", "Brooding Service", "Heat Source", "Incubator Repair"],
        "Farm Assets": ["Incubator", "Brooder", "Poultry House", "Feed Mixer", "Generator", "Water Tank", "Weighing Scale"],
        "Labour & Services": ["Farm Worker", "Poultry Attendant", "Veterinarian", "Vaccinator", "Cleaner", "Casual Worker"],
        "Farm Operations": ["Transport", "Slaughtering", "Packaging", "Equipment Rental", "Electricity", "Water", "Farm Rent", "Tax", "Insurance"],
    },
}

KG_ITEMS = {"Sand", "Aggregate", "Maize", "Soybean Meal", "Fish Meal", "Bran", "Premix", "Limestone", "Salt", "Manure", "Chicken Meat"}
SERVICE_WORDS = {"Service", "Repair", "Rental", "Rent", "Transport", "Tax", "Insurance", "Permit", "Security", "Electricity", "Water", "Slaughtering", "Packaging", "Masonry", "Roofing", "Plastering", "Flooring", "Painting", "Renovation", "New Building"}


def seed_catalog(apps, schema_editor):
    Group = apps.get_model("finance", "ObligationItemGroup")
    Item = apps.get_model("finance", "ObligationItemType")
    for business_unit, groups in CATALOG.items():
        for group_order, (group_name, items) in enumerate(groups.items(), 1):
            group, _ = Group.objects.update_or_create(
                business_unit=business_unit,
                name=group_name,
                defaults={"order": group_order, "is_active": True},
            )
            for item_order, name in enumerate(items, 1):
                unit = "kg" if name in KG_ITEMS else "service" if any(word in name for word in SERVICE_WORDS) else "piece"
                Item.objects.update_or_create(
                    item_group=group,
                    name=name,
                    defaults={"default_unit": unit, "order": item_order, "is_active": True},
                )


class Migration(migrations.Migration):
    dependencies = [("finance", "0011_harden_payable_reference_status")]
    operations = [
        migrations.CreateModel(
            name="ObligationItemGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("business_unit", models.CharField(choices=[("FURNITURE", "Furniture & Manufacturing"), ("CONSTRUCTION", "Construction & Built Environment"), ("AGRICULTURE", "Agriculture & Poultry")], db_index=True, max_length=30)),
                ("name", models.CharField(max_length=120)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("business_unit", "order", "name")},
        ),
        migrations.CreateModel(
            name="ObligationItemType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("default_unit", models.CharField(default="piece", max_length=30)),
                ("order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("item_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="item_types", to="finance.obligationitemgroup")),
            ],
            options={"ordering": ("item_group__order", "order", "name")},
        ),
        migrations.AddField(model_name="payable", name="item_group", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payables", to="finance.obligationitemgroup")),
        migrations.AddField(model_name="receivable", name="item_group", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="receivables", to="finance.obligationitemgroup")),
        migrations.AddField(model_name="obligationline", name="catalog_item", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="obligation_lines", to="finance.obligationitemtype")),
        migrations.AddConstraint(model_name="obligationitemgroup", constraint=models.UniqueConstraint(fields=("business_unit", "name"), name="fin_item_group_unique_name")),
        migrations.AddConstraint(model_name="obligationitemtype", constraint=models.UniqueConstraint(fields=("item_group", "name"), name="fin_item_type_unique_name")),
        migrations.RunPython(seed_catalog, migrations.RunPython.noop),
    ]
