from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStep:
    code: str
    name: str
    order: int
    requires_approval: bool = False


class WorkflowRegistry:
    WORKFLOWS = {
        "GENERIC": [
            WorkflowStep("DRAFT", "Draft", 1),
            WorkflowStep("SUBMITTED", "Submitted", 2),
            WorkflowStep("APPROVED", "Approved", 3, True),
            WorkflowStep("PROCESSING", "Processing", 4),
            WorkflowStep("COMPLETED", "Completed", 5),
        ],

        "FURNITURE_PRODUCTION": [
            WorkflowStep("QUOTATION", "Quotation", 1),
            WorkflowStep("APPROVED", "Approved", 2, True),
            WorkflowStep("ORDER_CONFIRMED", "Order Confirmed", 3),
            WorkflowStep("MATERIAL_RESERVED", "Material Reserved", 4),
            WorkflowStep("IN_PRODUCTION", "In Production", 5),
            WorkflowStep("QUALITY_CHECK", "Quality Check", 6),
            WorkflowStep("FINISHED_GOODS", "Finished Goods", 7),
            WorkflowStep("DELIVERED", "Delivered", 8),
        ],

        "CONSTRUCTION_PROJECT": [
            WorkflowStep("PLANNING", "Planning", 1),
            WorkflowStep("BUDGET_APPROVAL", "Budget Approval", 2, True),
            WorkflowStep("PROCUREMENT", "Procurement", 3),
            WorkflowStep("EXECUTION", "Execution", 4),
            WorkflowStep("INSPECTION", "Inspection", 5),
            WorkflowStep("COMPLETED", "Completed", 6),
        ],

        "FINANCE_PAYMENT": [
            WorkflowStep("DRAFT", "Draft", 1),
            WorkflowStep("SUBMITTED", "Submitted", 2),
            WorkflowStep("FINANCE_REVIEW", "Finance Review", 3),
            WorkflowStep("APPROVED", "Approved", 4, True),
            WorkflowStep("PAID", "Paid", 5),
        ],

        "MARKETPLACE_ORDER": [
            WorkflowStep("PLACED", "Placed", 1),
            WorkflowStep("CONFIRMED", "Confirmed", 2),
            WorkflowStep("PROCESSING", "Processing", 3),
            WorkflowStep("READY_FOR_DELIVERY", "Ready for Delivery", 4),
            WorkflowStep("DELIVERED", "Delivered", 5),
        ],
    }

    @classmethod
    def get_workflow(cls, workflow_code):
        return cls.WORKFLOWS.get(
            workflow_code,
            cls.WORKFLOWS["GENERIC"]
        )

    @classmethod
    def get_first_step(cls, workflow_code):
        return cls.get_workflow(workflow_code)[0]

    @classmethod
    def get_step(cls, workflow_code, step_code):
        for step in cls.get_workflow(workflow_code):
            if step.code == step_code:
                return step
        return None

    @classmethod
    def get_next_step(cls, workflow_code, current_step_code):
        workflow = cls.get_workflow(workflow_code)

        for index, step in enumerate(workflow):
            if step.code == current_step_code:
                if index + 1 < len(workflow):
                    return workflow[index + 1]
                return step

        return workflow[0]

    @classmethod
    def can_move_to(cls, workflow_code, current_step_code, next_step_code):
        next_step = cls.get_next_step(
            workflow_code,
            current_step_code
        )

        return next_step.code == next_step_code

    @classmethod
    def requires_approval(cls, workflow_code, step_code):
        step = cls.get_step(workflow_code, step_code)

        if not step:
            return False

        return step.requires_approval