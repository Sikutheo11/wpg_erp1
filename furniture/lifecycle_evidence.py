from decimal import Decimal

from .planner_models import ProductionPlan


class ProductionJobLifecycleEvidence:
    @classmethod
    def build(cls, job):
        order = job.order
        plans = ProductionPlan.objects.none()
        investment = None

        if order is not None:
            plans = ProductionPlan.objects.filter(order=order).order_by("-created_at", "-pk")
            try:
                investment = order.job_investment
            except Exception:
                investment = None

        approved_plan = plans.filter(status="APPROVED").first()
        calculated_plan = plans.filter(
            status__in={"CALCULATED", "UNDER_REVIEW", "APPROVED"}
        ).first()

        reservations = job.stock_reservations.all()
        outputs = job.outputs.all()

        output_quantity = sum(int(x.quantity_produced or 0) for x in outputs)
        released_quantity = sum(
            int(x.quantity_produced or 0)
            for x in outputs
            if getattr(x, "inventory_movement_id", None)
        )

        order_authorized = bool(
            order and getattr(order, "is_production_authorized", False)
        )

        delivery_complete = bool(
            order and (
                getattr(order, "delivery_status", None) == "DELIVERED"
                or getattr(order, "status", None) in {"DELIVERED", "COMPLETED"}
                or getattr(order, "delivered_at", None) is not None
            )
        )

        payment_complete = bool(
            order and getattr(order, "payment_status", None) == "PAID"
        )

        return {
            "order": {
                "exists": order is not None,
                "status": getattr(order, "status", None),
                "authorized": order_authorized,
                "number": getattr(order, "order_number", None),
            },
            "plan": {
                "exists": plans.exists(),
                "count": plans.count(),
                "calculated": calculated_plan is not None,
                "approved": approved_plan is not None,
                "approved_plan": approved_plan,
                "latest": plans.first(),
            },
            "funding": cls._funding_evidence(investment),
            "materials": {
                "reservation_count": reservations.count(),
                "reserved_count": reservations.filter(status="RESERVED").count(),
                "used_count": reservations.filter(status="USED").count(),
                "has_reservations": reservations.exists(),
                "ready": reservations.exists(),
            },
            "production": {
                "output_count": outputs.count(),
                "output_quantity": output_quantity,
                "target_quantity": int(job.quantity_to_produce or 0),
                "output_complete": (
                    output_quantity >= int(job.quantity_to_produce or 0)
                    if job.quantity_to_produce else False
                ),
            },
            "inventory": {
                "released_quantity": released_quantity,
                "all_output_released": (
                    output_quantity > 0 and released_quantity >= output_quantity
                ),
            },
            "delivery": {
                "complete": delivery_complete,
                "status": getattr(order, "delivery_status", None) if order else None,
                "delivered_at": getattr(order, "delivered_at", None) if order else None,
            },
            "finance": {
                "payment_complete": payment_complete,
                "payment_status": getattr(order, "payment_status", None) if order else None,
                "actual_revenue": (
                    investment.actual_revenue_snapshot
                    if investment is not None else Decimal("0.00")
                ),
                "actual_cost": (
                    investment.actual_cost_snapshot
                    if investment is not None else Decimal("0.00")
                ),
                "investment_status": investment.status if investment is not None else None,
            },
        }

    @staticmethod
    def _funding_evidence(investment):
        if investment is None:
            return {
                "exists": False,
                "required": False,
                "ready": True,
                "status": "NOT_OPENED",
                "estimated_cost": Decimal("0.00"),
                "funded_amount": Decimal("0.00"),
                "funding_gap": Decimal("0.00"),
                "message": (
                    "No Job Funding record is open. External funding is optional; "
                    "open it only when this job needs additional capital."
                ),
            }

        estimated = Decimal(str(investment.estimated_job_cost or 0))
        wpg = Decimal(str(investment.wpg_capital_committed or 0))
        investor = Decimal(str(investment.investor_capital_received or 0))
        funded = wpg + investor
        gap = max(estimated - funded, Decimal("0.00"))
        ready = gap <= 0 or investment.status in {
            "FUNDED", "ACTIVE", "SETTLEMENT", "CLOSED"
        }

        return {
            "exists": True,
            "required": True,
            "ready": ready,
            "status": investment.status,
            "estimated_cost": estimated,
            "funded_amount": funded,
            "funding_gap": gap,
            "message": (
                "Funding is sufficient."
                if ready
                else (
                    f"Funding gap remains {gap:,.0f} RWF. "
                    "Complete WPG/investor funding before material commitment."
                )
            ),
        }
