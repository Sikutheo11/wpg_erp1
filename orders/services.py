from django.db import transaction
from furniture.models import ProductionJob


class OrderService:
    @staticmethod
    @transaction.atomic
    def create_production_job_from_order(order, user=None):

        if hasattr(order, "production_job"):
            return order.production_job

        job_type = "CUSTOMER_CUSTOM"

        if order.order_type == "PRODUCTION":
            job_type = "RESTOCK"

        production_job = ProductionJob.objects.create(
            order=order,
            product=order.items.first().product if order.items.exists() else None,
            job_type=job_type,
            quantity_to_produce=order.items.first().quantity if order.items.exists() else 1,
            status="PENDING",
            description=order.notes or "",
        )

        order.status = "PROCESSING"
        order.save()

        return production_job