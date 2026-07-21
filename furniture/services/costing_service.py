from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from furniture.models import (
    ProductionJob,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    ProductionOutput,
    ProductionTaskLog,
    MachineUsageLog,
)


class ProductionCostService:
    """
    Furniture Manufacturing Costing Engine.

    Calculates:
    - actual material cost
    - actual labour cost
    - actual machine cost
    - overhead cost
    - total production cost
    - cost per produced unit
    - quotation cost
    - cost variance
    - revenue
    - actual profit or loss
    - gross margin
    """

    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    # =====================================================
    # HELPERS
    # =====================================================

    @classmethod
    def to_decimal(cls, value):
        if value in (None, ""):
            return cls.ZERO

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError(
                f"'{value}' cannot be converted to a monetary value."
            )

    @classmethod
    def money(cls, value):
        return cls.to_decimal(value).quantize(
            Decimal("0.01")
        )

    @classmethod
    def percentage(cls, value):
        return cls.to_decimal(value).quantize(
            Decimal("0.01")
        )

    @classmethod
    def _job_from_object(cls, obj):
        """
        Accept either ProductionJob or ProductionOutput.
        """
        if isinstance(obj, ProductionJob):
            return obj

        production_job = getattr(
            obj,
            "production_job",
            None,
        )

        if production_job is None:
            raise ValidationError(
                "A production job is required for costing."
            )

        return production_job

    # =====================================================
    # MATERIAL COST
    # =====================================================

    @classmethod
    def material_cost(cls, obj):
        job = cls._job_from_object(obj)

        expression = ExpressionWrapper(
            F("quantity_used") * F("unit_cost"),
            output_field=DecimalField(
                max_digits=20,
                decimal_places=4,
            ),
        )

        total = (
            ProductionMaterial.objects.filter(
                production_job=job
            )
            .aggregate(
                total=Coalesce(
                    Sum(expression),
                    cls.ZERO,
                    output_field=DecimalField(
                        max_digits=20,
                        decimal_places=4,
                    ),
                )
            )
            .get("total")
        )

        return cls.money(total)

    # =====================================================
    # LABOUR COST
    # =====================================================

    @classmethod
    def task_labour_cost(cls, obj):
        """
        Calculate labour from task work logs.

        Formula:
            hours worked × employee hourly rate
        """
        job = cls._job_from_object(obj)

        logs = (
            ProductionTaskLog.objects.filter(
                task__production_job=job,
                hours_worked__gt=0,
                employee__isnull=False,
            )
            .select_related("employee")
        )

        total = cls.ZERO

        for log in logs:
            hourly_rate = cls.to_decimal(
                getattr(
                    log.employee,
                    "hourly_rate",
                    cls.ZERO,
                )
            )

            total += (
                cls.to_decimal(log.hours_worked)
                * hourly_rate
            )

        return cls.money(total)


    @classmethod
    def manual_labour_cost(cls, obj):
        """
        Legacy/manual labour entries.
        Used only when no task-based labour logs exist.
        """
        job = cls._job_from_object(obj)

        expression = ExpressionWrapper(
            F("hours_worked") * F("hourly_rate"),
            output_field=DecimalField(
                max_digits=20,
                decimal_places=4,
            ),
        )

        total = (
            ProductionLabour.objects.filter(
                production_job=job,
            )
            .aggregate(
                total=Coalesce(
                    Sum(expression),
                    cls.ZERO,
                    output_field=DecimalField(
                        max_digits=20,
                        decimal_places=4,
                    ),
                )
            )
            .get("total")
        )

        return cls.money(total)


    @classmethod
    def labour_cost(cls, obj):
        """
        Task logs are the primary source.

        Manual ProductionLabour records are used only as fallback,
        preventing the same labour from being counted twice.
        """
        task_cost = cls.task_labour_cost(obj)

        if task_cost > 0:
            return task_cost

        return cls.manual_labour_cost(obj)

    # =====================================================
    # MACHINE COST
    # =====================================================
   
    @classmethod
    def task_machine_cost(cls, obj):
        """
        Calculate machine cost from task machine usage logs.
        """
        job = cls._job_from_object(obj)

        expression = ExpressionWrapper(
            F("hours_used") * F("hourly_cost"),
            output_field=DecimalField(
                max_digits=20,
                decimal_places=4,
            ),
        )

        total = (
            MachineUsageLog.objects.filter(
                task__production_job=job,
            )
            .aggregate(
                total=Coalesce(
                    Sum(expression),
                    cls.ZERO,
                    output_field=DecimalField(
                        max_digits=20,
                        decimal_places=4,
                    ),
                )
            )
            .get("total")
        )

        return cls.money(total)


    @classmethod
    def manual_machine_cost(cls, obj):
        """
        Legacy/manual machine records.
        Used only when task machine logs are absent.
        """
        job = cls._job_from_object(obj)

        expression = ExpressionWrapper(
            F("hours_used") * F("hourly_cost"),
            output_field=DecimalField(
                max_digits=20,
                decimal_places=4,
            ),
        )

        total = (
            ProductionMachine.objects.filter(
                production_job=job,
            )
            .aggregate(
                total=Coalesce(
                    Sum(expression),
                    cls.ZERO,
                    output_field=DecimalField(
                        max_digits=20,
                        decimal_places=4,
                    ),
                )
            )
            .get("total")
        )

        return cls.money(total)


    @classmethod
    def machine_cost(cls, obj):
        task_cost = cls.task_machine_cost(obj)

        if task_cost > 0:
            return task_cost

        return cls.manual_machine_cost(obj)

    # =====================================================
    # DIRECT COST
    # =====================================================

    @classmethod
    def direct_cost(cls, obj):
        return cls.money(
            cls.material_cost(obj)
            + cls.labour_cost(obj)
            + cls.machine_cost(obj)
        )

    # =====================================================
    # OVERHEAD COST
    # =====================================================

    @classmethod
    def overhead_cost(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        """
        Overhead can be calculated using:

        direct cost × overhead percentage
        plus
        fixed overhead amount.
        """
        rate = cls.to_decimal(overhead_rate)
        fixed = cls.to_decimal(fixed_overhead)

        if rate < 0:
            raise ValidationError(
                "Overhead rate cannot be negative."
            )

        if fixed < 0:
            raise ValidationError(
                "Fixed overhead cannot be negative."
            )

        percentage_cost = (
            cls.direct_cost(obj)
            * rate
            / cls.HUNDRED
        )

        return cls.money(
            percentage_cost + fixed
        )

    # =====================================================
    # TOTAL ACTUAL COST
    # =====================================================

    @classmethod
    def total_cost(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
        wastage_rate=Decimal("0.00"),
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
    ):
        direct = cls.direct_cost(obj)

        overhead = cls.overhead_cost(
            obj=obj,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
        )

        wastage = cls.wastage_cost(
            obj=obj,
            wastage_rate=wastage_rate,
        )

        additional = cls.additional_cost(
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        return cls.money(
            direct
            + overhead
            + wastage
            + additional
        )

    # =====================================================
    # OUTPUT QUANTITY
    # =====================================================

    @classmethod
    def output_quantity(cls, obj):
        job = cls._job_from_object(obj)

        total = (
            ProductionOutput.objects.filter(
                production_job=job
            )
            .aggregate(
                total=Coalesce(
                    Sum("quantity_produced"),
                    cls.ZERO,
                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2,
                    ),
                )
            )
            .get("total")
        )

        return cls.to_decimal(total)

    # =====================================================
    # COST PER UNIT
    # =====================================================

    @classmethod
    def cost_per_unit(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        quantity = cls.output_quantity(obj)

        if quantity <= 0:
            return cls.ZERO

        return cls.money(
            cls.total_cost(
                obj=obj,
                overhead_rate=overhead_rate,
                fixed_overhead=fixed_overhead,
            )
            / quantity
        )

    # =====================================================
    # QUOTATION
    # =====================================================

    @classmethod
    def quotation(cls, obj):
        job = cls._job_from_object(obj)

        try:
            return job.quotation
        except Exception:
            return None

    @classmethod
    def quotation_cost(cls, obj):
        quotation = cls.quotation(obj)

        if quotation is None:
            return cls.ZERO

        costs = [
            getattr(quotation, "material_cost", cls.ZERO),
            getattr(quotation, "labour_cost", cls.ZERO),
            getattr(quotation, "machine_cost", cls.ZERO),
            getattr(quotation, "transport_cost", cls.ZERO),
            getattr(quotation, "other_cost", cls.ZERO),
        ]

        return cls.money(
            sum(
                (
                    cls.to_decimal(value)
                    for value in costs
                ),
                cls.ZERO,
            )
        )

    @classmethod
    def quotation_selling_price(cls, obj):
        quotation = cls.quotation(obj)

        if quotation is None:
            return cls.ZERO

        return cls.money(
            getattr(
                quotation,
                "selling_price",
                cls.ZERO,
            )
        )

    # =====================================================
    # COST VARIANCE
    # =====================================================

    @classmethod
    def cost_variance(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        """
        Positive variance:
            actual cost is higher than quotation cost.

        Negative variance:
            actual cost is lower than quotation cost.
        """
        return cls.money(
            cls.total_cost(
                obj=obj,
                overhead_rate=overhead_rate,
                fixed_overhead=fixed_overhead,
            )
            - cls.quotation_cost(obj)
        )

    @classmethod
    def cost_variance_percentage(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        quoted_cost = cls.quotation_cost(obj)

        if quoted_cost <= 0:
            return cls.ZERO

        return cls.percentage(
            cls.cost_variance(
                obj=obj,
                overhead_rate=overhead_rate,
                fixed_overhead=fixed_overhead,
            )
            / quoted_cost
            * cls.HUNDRED
        )

    # =====================================================
    # REVENUE
    # =====================================================

    @classmethod
    def expected_revenue(cls, obj):
        job = cls._job_from_object(obj)
        quotation = cls.quotation(job)

        # Approved quotation is the primary commercial value.
        if quotation is not None:
            quotation_status = str(
                getattr(quotation, "status", "")
            ).upper()

            selling_price = cls.to_decimal(
                getattr(
                    quotation,
                    "selling_price",
                    cls.ZERO,
                )
            )

            if (
                quotation_status == "APPROVED"
                and selling_price > 0
            ):
                return cls.money(selling_price)

        # Product catalogue value is a fallback only.
        if job.product is None:
            return cls.ZERO

        quantity = cls.output_quantity(job)

        if quantity <= 0:
            quantity = cls.to_decimal(
                job.quantity_to_produce
            )

        return cls.money(
            cls.to_decimal(job.product.selling_price)
            * quantity
        )

    # =====================================================
    # PROFIT
    # =====================================================

    @classmethod
    def actual_profit(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
        wastage_rate=Decimal("0.00"),
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
    ):
        revenue = cls.expected_revenue(obj)

        actual_cost = cls.total_cost(
            obj=obj,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
            wastage_rate=wastage_rate,
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        return cls.money(
            revenue - actual_cost
        )

    @classmethod
    def profit_per_unit(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        quantity = cls.output_quantity(obj)

        if quantity <= 0:
            return cls.ZERO

        return cls.money(
            cls.actual_profit(
                obj=obj,
                overhead_rate=overhead_rate,
                fixed_overhead=fixed_overhead,
            )
            / quantity
        )

    @classmethod
    def profit_margin(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
        wastage_rate=Decimal("0.00"),
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
    ):
        revenue = cls.expected_revenue(obj)

        if revenue <= 0:
            return cls.ZERO

        profit = cls.actual_profit(
            obj=obj,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
            wastage_rate=wastage_rate,
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        return cls.percentage(
            profit / revenue * cls.HUNDRED
        )

    @classmethod
    def expected_profit(cls, obj):
        quotation = cls.quotation(obj)

        if quotation is None:
            return cls.ZERO

        selling_price = cls.quotation_selling_price(obj)
        quoted_cost = cls.quotation_cost(obj)

        return cls.money(
            selling_price - quoted_cost
        )

    @classmethod
    def profit_variance(
        cls,
        obj,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
    ):
        return cls.money(
            cls.actual_profit(
                obj=obj,
                overhead_rate=overhead_rate,
                fixed_overhead=fixed_overhead,
            )
            - cls.expected_profit(obj)
        )

    # =====================================================
    # JOB COST SUMMARY
    # =====================================================

    @classmethod
    def job_cost_summary(
        cls,
        production_job,
        overhead_rate=Decimal("0.00"),
        fixed_overhead=Decimal("0.00"),
        wastage_rate=Decimal("0.00"),
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
    ):
        material = cls.material_cost(
            production_job
        )

        labour = cls.labour_cost(
            production_job
        )

        machine = cls.machine_cost(
            production_job
        )

        direct = cls.money(
            material + labour + machine
        )

        overhead = cls.overhead_cost(
            obj=production_job,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
        )

        wastage = cls.wastage_cost(
            obj=production_job,
            wastage_rate=wastage_rate,
        )

        additional = cls.additional_cost(
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        actual_total = cls.total_cost(
            obj=production_job,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
            wastage_rate=wastage_rate,
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        quantity = cls.output_quantity(
            production_job
        )

        revenue = cls.expected_revenue(
            production_job
        )

        profit = cls.actual_profit(
            obj=production_job,
            overhead_rate=overhead_rate,
            fixed_overhead=fixed_overhead,
            wastage_rate=wastage_rate,
            transport_cost=transport_cost,
            other_cost=other_cost,
        )

        quotation_cost = cls.quotation_cost(
            production_job
        )

        variance = cls.money(
            actual_total - quotation_cost
        )

        if quotation_cost > 0:
            variance_percentage = cls.percentage(
                variance
                / quotation_cost
                * cls.HUNDRED
            )
        else:
            variance_percentage = cls.ZERO

        if quantity > 0:
            cost_per_unit = cls.money(
                actual_total / quantity
            )

            profit_per_unit = cls.money(
                profit / quantity
            )
        else:
            cost_per_unit = cls.ZERO
            profit_per_unit = cls.ZERO

        margin = (
            cls.percentage(
                profit / revenue * cls.HUNDRED
            )
            if revenue > 0
            else cls.ZERO
        )

        return {
            "production_job": production_job,

            # Actual costs
            "material_cost": material,
            "labour_cost": labour,
            "machine_cost": machine,
            "direct_cost": direct,
            "overhead_cost": overhead,
            "wastage_cost": wastage,
            "additional_cost": additional,
            "actual_total_cost": actual_total,

            # Quantity performance
            "planned_quantity": cls.planned_quantity(
                production_job
            ),
            "output_quantity": quantity,
            "quantity_variance": cls.quantity_variance(
                production_job
            ),
            "completion_rate": cls.completion_rate(
                production_job
            ),

            # Unit economics
            "cost_per_unit": cost_per_unit,
            "profit_per_unit": profit_per_unit,

            # Quotation comparison
            "quotation_cost": quotation_cost,
            "quotation_selling_price": (
                cls.quotation_selling_price(
                    production_job
                )
            ),
            "cost_variance": variance,
            "cost_variance_percentage": (
                variance_percentage
            ),

            # Commercial performance
            "expected_revenue": revenue,
            "expected_profit": cls.expected_profit(
                production_job
            ),
            "actual_profit": profit,
            "profit_margin": margin,
            "profit_variance": cls.money(
                profit
                - cls.expected_profit(
                    production_job
                )
            ),

            # Decisions
            "is_profitable": profit >= 0,
            "is_loss_making": profit < 0,
            "is_over_budget": (
                quotation_cost > 0
                and variance > 0
            ),
            "has_quotation": (
                cls.quotation(
                    production_job
                )
                is not None
            ),
        }
    # =====================================================
# WASTAGE AND ADDITIONAL COSTS
# =====================================================

    @classmethod
    def wastage_cost(
        cls,
        obj,
        wastage_rate=Decimal("0.00"),
    ):
        """
        Apply wastage percentage to actual material cost.
        """
        rate = cls.to_decimal(wastage_rate)

        if rate < 0:
            raise ValidationError(
                "Wastage rate cannot be negative."
            )

        return cls.money(
            cls.material_cost(obj)
            * rate
            / cls.HUNDRED
        )


    @classmethod
    def additional_cost(
        cls,
        transport_cost=Decimal("0.00"),
        other_cost=Decimal("0.00"),
    ):
        transport = cls.to_decimal(transport_cost)
        other = cls.to_decimal(other_cost)

        if transport < 0:
            raise ValidationError(
                "Transport cost cannot be negative."
            )

        if other < 0:
            raise ValidationError(
                "Other cost cannot be negative."
            )

        return cls.money(
            transport + other
        )

    # =====================================================
# QUANTITY PERFORMANCE
# =====================================================

    @classmethod
    def planned_quantity(cls, obj):
        job = cls._job_from_object(obj)

        return cls.to_decimal(
            job.quantity_to_produce
        )


    @classmethod
    def quantity_variance(cls, obj):
        return cls.to_decimal(
            cls.output_quantity(obj)
            - cls.planned_quantity(obj)
        )


    @classmethod
    def completion_rate(cls, obj):
        planned = cls.planned_quantity(obj)

        if planned <= 0:
            return cls.ZERO

        return cls.percentage(
            cls.output_quantity(obj)
            / planned
            * cls.HUNDRED
        )