from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from agriculture.models import AgricultureOperation, PoultryFarm
from agriculture.services.operation_service import AgricultureOperationService
from inventory.models import Category, Product


PRODUCTS = (
    {
        "product_code": "AGR-DOC",
        "name": "Day-old Chick",
        "product_type": "LIVESTOCK",
        "unit": "bird",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Day-old poultry chick for brooding, sale or flock setup.",
    },
    {
        "product_code": "AGR-LAYER-BIRD",
        "name": "Layer Chicken",
        "product_type": "LIVESTOCK",
        "unit": "bird",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Layer chicken represented in the shared Inventory Engine.",
    },
    {
        "product_code": "AGR-BROILER-BIRD",
        "name": "Broiler Chicken",
        "product_type": "LIVESTOCK",
        "unit": "bird",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Broiler chicken represented in the shared Inventory Engine.",
    },
    {
        "product_code": "AGR-BREEDER-BIRD",
        "name": "Breeder Chicken",
        "product_type": "LIVESTOCK",
        "unit": "bird",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Breeding poultry stock represented in Inventory.",
    },
    {
        "product_code": "AGR-TABLE-EGG",
        "name": "Table Egg",
        "product_type": "AGRICULTURE_OUTPUT",
        "unit": "egg",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Saleable egg produced by an Agriculture layer flock.",
    },
    {
        "product_code": "AGR-HATCHING-EGG",
        "name": "Hatching Egg",
        "product_type": "AGRICULTURE_OUTPUT",
        "unit": "egg",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Fertile egg selected for incubation.",
    },
    {
        "product_code": "AGR-POULTRY-MEAT",
        "name": "Poultry Meat",
        "product_type": "AGRICULTURE_OUTPUT",
        "unit": "kg",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Processed poultry meat available for sale or fulfilment.",
    },
    {
        "product_code": "AGR-MANURE",
        "name": "Poultry Manure",
        "product_type": "AGRICULTURE_OUTPUT",
        "unit": "kg",
        "valuation_method": "WEIGHTED_AVERAGE",
        "description": "Poultry manure collected as a saleable farm by-product.",
    },
    {
        "product_code": "AGR-CHICK-STARTER",
        "name": "Chick Starter Feed",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "kg",
        "valuation_method": "FIFO",
        "description": "Starter feed used during chick brooding.",
    },
    {
        "product_code": "AGR-BROILER-STARTER",
        "name": "Broiler Starter Feed",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "kg",
        "valuation_method": "FIFO",
        "description": "Starter feed for broiler flocks.",
    },
    {
        "product_code": "AGR-BROILER-GROWER",
        "name": "Broiler Grower Feed",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "kg",
        "valuation_method": "FIFO",
        "description": "Grower feed for broiler flocks.",
    },
    {
        "product_code": "AGR-BROILER-FINISHER",
        "name": "Broiler Finisher Feed",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "kg",
        "valuation_method": "FIFO",
        "description": "Finisher feed for market-ready broiler flocks.",
    },
    {
        "product_code": "AGR-LAYER-MASH",
        "name": "Layer Mash Feed",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "kg",
        "valuation_method": "FIFO",
        "description": "Production feed for laying poultry.",
    },
    {
        "product_code": "AGR-VACCINE",
        "name": "Poultry Vaccine",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "dose",
        "valuation_method": "FIFO",
        "description": "Poultry vaccine stock used in health operations.",
    },
    {
        "product_code": "AGR-MEDICINE",
        "name": "Poultry Medicine",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "unit",
        "valuation_method": "FIFO",
        "description": "General poultry medicine stock.",
    },
    {
        "product_code": "AGR-DISINFECTANT",
        "name": "Poultry House Disinfectant",
        "product_type": "AGRICULTURE_INPUT",
        "unit": "litre",
        "valuation_method": "FIFO",
        "description": "Disinfectant used for poultry-house biosecurity.",
    },
)


STANDARD_OPERATIONS = (
    ("FLOCK_SETUP", "Standard flock establishment and acquisition operation."),
    ("EGG_PRODUCTION", "Standard egg collection and production operation."),
    ("INCUBATION", "Standard egg incubation and hatching operation."),
    ("BROODING", "Standard chick brooding operation."),
    ("GROW_OUT", "Standard poultry grow-out operation."),
    ("FEEDING", "Standard flock feeding programme."),
    ("HEALTH", "Standard poultry health and vaccination operation."),
    ("RESTOCK", "Standard Agriculture inventory restock operation."),
    (
        "ORDER_FULFILMENT",
        "Standard Agriculture customer-order fulfilment operation.",
    ),
)


class Command(BaseCommand):
    help = (
        "Seed the shared Agriculture inventory catalogue and create idempotent "
        "draft operations for one poultry farm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--farm-id",
            type=int,
            help="PoultryFarm primary key used for standard operations.",
        )
        parser.add_argument(
            "--actor",
            help=(
                "Optional value of the configured user model's USERNAME_FIELD "
                "to record as the operation creator."
            ),
        )
        parser.add_argument(
            "--products-only",
            action="store_true",
            help="Create only the shared Inventory products.",
        )
        parser.add_argument(
            "--operations-only",
            action="store_true",
            help="Create only the farm operations.",
        )

    def handle(self, *args, **options):
        if options["products_only"] and options["operations_only"]:
            raise CommandError(
                "--products-only and --operations-only cannot be used together."
            )

        create_products = not options["operations_only"]
        create_operations = not options["products_only"]

        if create_operations and not options["farm_id"]:
            raise CommandError(
                "--farm-id is required unless --products-only is supplied."
            )

        actor = self._resolve_actor(options.get("actor"))

        with transaction.atomic():
            if create_products:
                self._seed_products()

            if create_operations:
                self._seed_operations(
                    farm_id=options["farm_id"],
                    actor=actor,
                )

        self.stdout.write(self.style.SUCCESS("Agriculture business data is ready."))

    def _resolve_actor(self, actor_value):
        if not actor_value:
            return None

        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD

        try:
            return user_model._default_manager.get(
                **{username_field: actor_value}
            )
        except user_model.DoesNotExist as error:
            raise CommandError(
                f"No user has {username_field}={actor_value!r}."
            ) from error

    def _seed_products(self):
        category, category_created = Category.objects.get_or_create(
            name="Agriculture / Poultry",
            defaults={
                "description": (
                    "Shared inventory catalogue for WPG Agriculture and Poultry."
                ),
                "is_active": True,
            },
        )

        category_action = "Created" if category_created else "Using"
        self.stdout.write(f"{category_action} category: {category.name}")

        created_count = 0
        existing_count = 0

        for definition in PRODUCTS:
            product_code = definition["product_code"]
            defaults = {
                key: value
                for key, value in definition.items()
                if key != "product_code"
            }
            defaults.update(
                {
                    "business_unit": "AGRICULTURE",
                    "category": category,
                    "selling_price": Decimal("0.00"),
                    "standard_cost": Decimal("0.00"),
                    "reorder_level": Decimal("0.00"),
                    "reorder_quantity": Decimal("0.00"),
                    "track_inventory": True,
                    "allow_negative_stock": False,
                    "is_active": True,
                    "is_published": False,
                    "is_featured": False,
                }
            )

            product, created = Product.objects.get_or_create(
                product_code=product_code,
                defaults=defaults,
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created product: {product.product_code} - {product.name}"
                    )
                )
            else:
                existing_count += 1
                self.stdout.write(
                    f"Product already exists: "
                    f"{product.product_code} - {product.name}"
                )

        self.stdout.write(
            f"Products: {created_count} created, {existing_count} already existed."
        )

    def _seed_operations(self, *, farm_id, actor):
        try:
            farm = PoultryFarm.objects.select_related(
                "manager",
                "warehouse",
            ).get(pk=farm_id)
        except PoultryFarm.DoesNotExist as error:
            raise CommandError(
                f"PoultryFarm with id={farm_id} does not exist."
            ) from error

        if not farm.is_active:
            raise CommandError(f"Farm {farm.code} is inactive.")

        if farm.warehouse_id is None:
            raise CommandError(
                f"Farm {farm.code} has no Agriculture warehouse assigned."
            )

        if farm.warehouse.business_unit != "AGRICULTURE":
            raise CommandError(
                f"Warehouse {farm.warehouse} does not belong to Agriculture."
            )

        created_count = 0
        existing_count = 0

        for operation_type, description in STANDARD_OPERATIONS:
            code = f"AGR-{farm.pk}-{operation_type}"
            existing = AgricultureOperation.objects.filter(code=code).first()

            if existing is not None:
                existing_count += 1
                self.stdout.write(
                    f"Operation already exists: "
                    f"{existing.code} ({existing.get_status_display()})"
                )
                continue

            operation = AgricultureOperationService.create_operation(
                operation_type=operation_type,
                farm=farm,
                actor=actor,
                assigned_to=farm.manager,
                budget=Decimal("0.00"),
                notes=(
                    f"[STANDARD_SETUP] {description} "
                    "Review, budget, submit and approve before execution."
                ),
                code=code,
            )
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created operation: {operation.code} "
                    f"({operation.get_operation_type_display()})"
                )
            )

        self.stdout.write(
            f"Operations for {farm.code}: {created_count} created, "
            f"{existing_count} already existed."
        )
