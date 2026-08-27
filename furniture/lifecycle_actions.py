from django.urls import NoReverseMatch, reverse


class ProductionJobLifecycleActions:
    @staticmethod
    def _url(name, *args):
        try:
            return reverse(name, args=args)
        except NoReverseMatch:
            return None

    @classmethod
    def build(cls, *, job, evidence, inspection=None):
        order = job.order
        latest_plan = evidence["plan"].get("latest")
        investment = None

        if order is not None:
            try:
                investment = order.job_investment
            except Exception:
                investment = None

        actions = []

        def add(code, label, url, style="outline-primary", enabled=True, note=""):
            if not url:
                enabled = False
            actions.append({
                "code": code,
                "label": label,
                "url": url,
                "style": style,
                "enabled": enabled,
                "note": note,
            })

        if job.product_id:
            add(
                "PRODUCT",
                "Open Product",
                cls._url("furniture:furniture_product_detail", job.product_id),
                note="Furniture product control page.",
            )

        if order is not None:
            add(
                "ORDER",
                "Open Order",
                cls._url("orders:order_detail", order.pk),
                note="Commercial order and delivery owner.",
            )

        if latest_plan is not None:
            add(
                "PLAN",
                "Open Production Plan",
                cls._url("furniture:planner_detail", latest_plan.pk),
                style="outline-info",
                note=f"Latest plan status: {latest_plan.status}.",
            )
        else:
            add(
                "PLAN",
                "Create Production Plan",
                cls._url("furniture:planner_create"),
                style="info",
                enabled=order is not None,
                note=(
                    "Create the technical/financial plan before production."
                    if order is not None
                    else "A linked enterprise Order is required first."
                ),
            )

        if order is not None:
            if investment is not None:
                add(
                    "FUNDING",
                    "Open Job Funding",
                    cls._url("core:job_investment_detail", investment.pk),
                    style="outline-success" if evidence["funding"]["ready"] else "danger",
                    note=evidence["funding"]["message"],
                )
            else:
                add(
                    "FUNDING",
                    "Open Funding Check",
                    cls._url("core:job_investment_open", order.pk),
                    style="outline-secondary",
                    note=(
                        "Optional: open Job Funding only when this job needs "
                        "external or ring-fenced capital."
                    ),
                )

        add(
            "TASKS",
            "Production Tasks",
            cls._url("furniture:production_task_list"),
            note="Manage workshop execution tasks.",
        )

        if job.status == "IN_PRODUCTION":
            add(
                "OUTPUT",
                "Record Output",
                cls._url("furniture:add_output", job.pk),
                style="outline-dark",
                note="Output stays in Furniture until final quality approval.",
            )

        if job.status in {"IN_PRODUCTION", "QUALITY_CHECK"}:
            if inspection is None:
                add(
                    "QUALITY",
                    "Create Final Inspection",
                    cls._url("furniture:quality_inspection_create", job.pk),
                    style="warning",
                    note="Required before finished-goods release.",
                )
            else:
                add(
                    "QUALITY",
                    "Open Quality Inspection",
                    cls._url("furniture:quality_inspection_detail", inspection.pk),
                    style="success" if inspection.result == "PASSED" and inspection.approved_at else "warning",
                    note=f"Latest result: {inspection.result}.",
                )

        if job.status == "READY_FOR_FINISHED_GOODS":
            add(
                "INVENTORY",
                "Release to Inventory",
                cls._url("furniture:production_job_detail", job.pk),
                style="success",
                note="Use the Finished Goods release control on this page.",
            )

        if order is not None and job.status == "FINISHED_GOODS":
            add(
                "SYNC_DELIVERY",
                "Confirm Order Delivery",
                cls._url("furniture:production_job_confirm_delivery", job.pk),
                style="success" if evidence["delivery"]["complete"] else "outline-secondary",
                enabled=evidence["delivery"]["complete"],
                note=(
                    "Mirror completed delivery from the Order Engine."
                    if evidence["delivery"]["complete"]
                    else "Complete delivery in the Order Engine first."
                ),
            )

        if job.status == "DELIVERED":
            add(
                "ENTER_FINANCE",
                "Start Finance / Profit Review",
                cls._url("furniture:production_job_move_to_finance", job.pk),
                style="warning",
                note="Move delivered production into final financial reconciliation.",
            )

        if job.status == "FINANCE":
            investment_status = evidence["finance"].get("investment_status")
            can_close = (
                evidence["delivery"]["complete"]
                and evidence["finance"]["payment_complete"]
                and (
                    not investment_status
                    or investment_status in {"CLOSED", "CANCELLED"}
                )
            )
            add(
                "CLOSE_JOB",
                "Close Production Job",
                cls._url("furniture:production_job_close", job.pk),
                style="success",
                enabled=can_close,
                note=(
                    "All delivery and financial obligations are complete."
                    if can_close
                    else "Payment reconciliation and any investor settlement must be complete."
                ),
            )

        if order is not None and job.status in {"FINISHED_GOODS", "DELIVERED", "FINANCE"}:
            add(
                "DELIVERY",
                "Open Delivery Workflow",
                cls._url("orders:order_detail", order.pk),
                style="success" if evidence["delivery"]["complete"] else "primary",
                note=(
                    "Delivery complete."
                    if evidence["delivery"]["complete"]
                    else "Dispatch/delivery is controlled by the Order Engine."
                ),
            )

        if order is not None and job.status in {"DELIVERED", "FINANCE", "CLOSED"}:
            add(
                "FINANCE",
                "Review Finance / Profit",
                (
                    cls._url("core:job_investment_detail", investment.pk)
                    if investment is not None
                    else cls._url("orders:order_detail", order.pk)
                ),
                style="success" if evidence["finance"]["payment_complete"] else "outline-warning",
                note=(
                    "Review payment, actual revenue/cost and investor settlement "
                    "where applicable."
                ),
            )

        return actions
