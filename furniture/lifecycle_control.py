class ProductionJobLifecycleControl:
    STAGES = (
        ("DESIGN", "Design"),
        ("COSTING", "Costing / BOM"),
        ("QUOTATION", "Quotation"),
        ("ORDER_CONFIRMED", "Order Confirmed"),
        ("PRODUCTION_PLAN", "Production Plan"),
        ("FUNDING_CHECK", "Funding Check"),
        ("MATERIAL_RESERVED", "Materials Reserved"),
        ("IN_PRODUCTION", "In Production"),
        ("QUALITY_CHECK", "Quality Check"),
        ("READY_FOR_FINISHED_GOODS", "Ready for Finished Goods"),
        ("FINISHED_GOODS", "Inventory / Finished Goods"),
        ("DELIVERY", "Delivery"),
        ("FINANCE", "Finance / Profit"),
        ("CLOSED", "Closed"),
    )

    STATUS_STAGE = {
        "DRAFT": "DESIGN", "DESIGN": "DESIGN", "COSTING": "COSTING",
        "QUOTATION": "QUOTATION", "APPROVED": "MATERIAL_RESERVED",
        "ORDER_CONFIRMED": "ORDER_CONFIRMED", "PRODUCTION_PLAN": "PRODUCTION_PLAN",
        "FUNDING_CHECK": "FUNDING_CHECK", "MATERIAL_RESERVED": "MATERIAL_RESERVED",
        "IN_PRODUCTION": "IN_PRODUCTION", "QUALITY_CHECK": "QUALITY_CHECK",
        "READY_FOR_FINISHED_GOODS": "READY_FOR_FINISHED_GOODS",
        "FINISHED_GOODS": "FINISHED_GOODS", "DELIVERED": "DELIVERY",
        "FINANCE": "FINANCE", "CLOSED": "CLOSED", "CANCELLED": "CLOSED",
    }

    @classmethod
    def build(cls, *, job, quotation=None, inspection=None):
        current_code = cls.STATUS_STAGE.get(job.status, "DESIGN")
        codes = [code for code, _ in cls.STAGES]
        current_index = codes.index(current_code) if current_code in codes else 0
        stages = []
        for index, (code, label) in enumerate(cls.STAGES):
            if job.status == "CANCELLED":
                state = "CANCELLED"
            elif index < current_index:
                state = "COMPLETED"
            elif index == current_index:
                state = "CURRENT"
            else:
                state = "PENDING"
            stages.append({"code": code, "label": label, "state": state})
        return {
            "current_code": current_code,
            "current_label": dict(cls.STAGES).get(current_code, job.get_status_display()),
            "stages": stages,
            "next_action": cls._next_action(job=job, quotation=quotation, inspection=inspection),
        }

    @classmethod
    def _next_action(cls, *, job, quotation=None, inspection=None):
        s = job.status
        if s in {"DRAFT", "DESIGN"}:
            return {"title": "Complete product design", "description": "Confirm product specifications before costing and planning."}
        if s == "COSTING":
            return {"title": "Complete costing and BOM", "description": "Complete material, labour, machine and additional estimated costs."}
        if s == "QUOTATION":
            return {"title": "Prepare quotation" if quotation is None else "Complete quotation approval",
                    "description": "Complete the commercial quotation workflow before production authorization."}
        if s == "ORDER_CONFIRMED":
            return {"title": "Prepare production plan", "description": "Create or approve the technical and financial production plan."}
        if s == "PRODUCTION_PLAN":
            return {"title": "Approve production plan", "description": "Approve estimated cost and production requirements."}
        if s == "FUNDING_CHECK":
            return {"title": "Complete funding check", "description": "Confirm sufficient approved funding before material commitment."}
        if s in {"MATERIAL_RESERVED", "APPROVED"}:
            return {"title": "Reserve materials", "description": "Confirm required materials are reserved or available before production starts."}
        if s == "IN_PRODUCTION":
            return {"title": "Complete production", "description": "Complete tasks and record output. Output does not enter Inventory yet."}
        if s == "QUALITY_CHECK":
            if inspection is None:
                return {"title": "Perform final quality inspection", "description": "Final output must pass quality inspection before Inventory release."}
            if inspection.result != "PASSED":
                return {"title": "Resolve quality failure / rework", "description": "Complete rework and perform another inspection."}
            if not inspection.approved_by_id:
                return {"title": "Approve final quality inspection", "description": "Passed final inspection must be formally approved."}
            return {"title": "Mark ready for finished goods", "description": "Quality is complete; move the job to Ready for Finished Goods."}
        if s == "READY_FOR_FINISHED_GOODS":
            return {"title": "Release to Inventory", "description": "Release approved output to a Furniture Finished Goods warehouse."}
        if s == "FINISHED_GOODS":
            return {"title": "Prepare delivery", "description": "Finished goods can now proceed to customer delivery."}
        if s == "DELIVERED":
            return {"title": "Complete finance and profitability review", "description": "Confirm revenue, costs, settlements and final profit."}
        if s == "FINANCE":
            return {"title": "Close production job", "description": "Complete reconciliation and close the job."}
        if s == "CLOSED":
            return {"title": "Workflow completed", "description": "Production, delivery and finance are complete."}
        if s == "CANCELLED":
            return {"title": "Job cancelled", "description": "No further production action is required."}
        return {"title": "Review production job", "description": "Review the job and determine the next required action."}
