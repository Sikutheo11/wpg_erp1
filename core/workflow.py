# core/workflow.py

from dataclasses import dataclass
from typing import Optional


# =====================================================
# WORKFLOW STEP
# =====================================================

@dataclass(frozen=True)
class WorkflowStep:
    """
    Represents one state/step in a workflow.
    """

    code: str
    name: str
    order: int

    requires_approval: bool = False
    is_terminal: bool = False

    color: str = "secondary"
    icon: str = "fas fa-circle"


# =====================================================
# WORKFLOW TRANSITION
# =====================================================

@dataclass(frozen=True)
class WorkflowTransitionDefinition:
    """
    Represents an allowed movement between two workflow steps.

    feature_code:
        Feature code checked by PermissionService.

    permission_action:
        One of:
        view, add, edit, delete, approve.

    requires_note:
        Whether the user must provide a reason/note.

    event_code:
        EventEngine event dispatched after a successful move.
    """

    from_step: str
    to_step: str

    name: str = ""

    feature_code: Optional[str] = None
    permission_action: str = "edit"

    requires_note: bool = False

    event_code: Optional[str] = None
    event_level: str = "INFO"

    is_approval: bool = False


# =====================================================
# WORKFLOW DEFINITION
# =====================================================

@dataclass(frozen=True)
class WorkflowDefinition:
    """
    Complete workflow definition.
    """

    code: str
    name: str

    steps: tuple[WorkflowStep, ...]
    transitions: tuple[WorkflowTransitionDefinition, ...]


# =====================================================
# WORKFLOW REGISTRY
# =====================================================

class WorkflowRegistry:
    """
    Enterprise workflow registry for WPG BOS.

    Responsibilities:
    - store workflow definitions;
    - expose steps and transitions;
    - validate workflow movements;
    - return available actions;
    - remain backward-compatible with the old linear workflow API.
    """

    WORKFLOWS = {

        # =================================================
        # GENERIC WORKFLOW
        # =================================================

        "GENERIC": WorkflowDefinition(
            code="GENERIC",
            name="Generic Workflow",

            steps=(
                WorkflowStep(
                    code="DRAFT",
                    name="Draft",
                    order=1,
                    color="secondary",
                    icon="fas fa-file",
                ),
                WorkflowStep(
                    code="SUBMITTED",
                    name="Submitted",
                    order=2,
                    color="warning",
                    icon="fas fa-paper-plane",
                ),
                WorkflowStep(
                    code="APPROVED",
                    name="Approved",
                    order=3,
                    requires_approval=True,
                    color="success",
                    icon="fas fa-check",
                ),
                WorkflowStep(
                    code="REJECTED",
                    name="Rejected",
                    order=4,
                    is_terminal=True,
                    color="danger",
                    icon="fas fa-times",
                ),
                WorkflowStep(
                    code="PROCESSING",
                    name="Processing",
                    order=5,
                    color="primary",
                    icon="fas fa-cogs",
                ),
                WorkflowStep(
                    code="COMPLETED",
                    name="Completed",
                    order=6,
                    is_terminal=True,
                    color="success",
                    icon="fas fa-check-double",
                ),
                WorkflowStep(
                    code="CANCELLED",
                    name="Cancelled",
                    order=7,
                    is_terminal=True,
                    color="danger",
                    icon="fas fa-ban",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    from_step="DRAFT",
                    to_step="SUBMITTED",
                    name="Submit",
                    permission_action="edit",
                    event_code="WORKFLOW_SUBMITTED",
                ),
                WorkflowTransitionDefinition(
                    from_step="SUBMITTED",
                    to_step="APPROVED",
                    name="Approve",
                    permission_action="approve",
                    is_approval=True,
                    event_code="WORKFLOW_APPROVED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="SUBMITTED",
                    to_step="REJECTED",
                    name="Reject",
                    permission_action="approve",
                    requires_note=True,
                    is_approval=True,
                    event_code="WORKFLOW_REJECTED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="APPROVED",
                    to_step="PROCESSING",
                    name="Start Processing",
                    permission_action="edit",
                    event_code="WORKFLOW_PROCESSING",
                ),
                WorkflowTransitionDefinition(
                    from_step="PROCESSING",
                    to_step="COMPLETED",
                    name="Complete",
                    permission_action="edit",
                    event_code="WORKFLOW_COMPLETED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="DRAFT",
                    to_step="CANCELLED",
                    name="Cancel",
                    permission_action="delete",
                    requires_note=True,
                    event_code="WORKFLOW_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="SUBMITTED",
                    to_step="CANCELLED",
                    name="Cancel",
                    permission_action="delete",
                    requires_note=True,
                    event_code="WORKFLOW_CANCELLED",
                    event_level="WARNING",
                ),
            ),
        ),

        # =================================================
        # SALES QUOTATION
        #
        # Status codes are lowercase because SalesQuotation
        # currently stores lowercase status values.
        # =================================================

        "SALES_QUOTATION": WorkflowDefinition(
            code="SALES_QUOTATION",
            name="Sales Quotation Workflow",

            steps=(
                WorkflowStep(
                    code="draft",
                    name="Draft",
                    order=1,
                    color="secondary",
                    icon="fas fa-file-alt",
                ),
                WorkflowStep(
                    code="sent",
                    name="Submitted",
                    order=2,
                    color="warning",
                    icon="fas fa-paper-plane",
                ),
                WorkflowStep(
                    code="approved",
                    name="Approved",
                    order=3,
                    requires_approval=True,
                    color="success",
                    icon="fas fa-check-circle",
                ),
                WorkflowStep(
                    code="rejected",
                    name="Rejected",
                    order=4,
                    color="danger",
                    icon="fas fa-times-circle",
                ),
                WorkflowStep(
                    code="converted",
                    name="Converted to Order",
                    order=5,
                    is_terminal=True,
                    color="primary",
                    icon="fas fa-exchange-alt",
                ),
                WorkflowStep(
                    code="cancelled",
                    name="Cancelled",
                    order=6,
                    is_terminal=True,
                    color="danger",
                    icon="fas fa-ban",
                ),
                WorkflowStep(
                    code="expired",
                    name="Expired",
                    order=7,
                    is_terminal=True,
                    color="dark",
                    icon="fas fa-clock",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    from_step="draft",
                    to_step="sent",
                    name="Submit Quotation",
                    feature_code="SALES_QUOTATION_SUBMIT",
                    permission_action="edit",
                    event_code="SALES_QUOTATION_SENT",
                ),
                WorkflowTransitionDefinition(
                    from_step="rejected",
                    to_step="sent",
                    name="Resubmit Quotation",
                    feature_code="SALES_QUOTATION_SUBMIT",
                    permission_action="edit",
                    event_code="SALES_QUOTATION_RESUBMITTED",
                ),
                WorkflowTransitionDefinition(
                    from_step="sent",
                    to_step="approved",
                    name="Approve Quotation",
                    feature_code="SALES_QUOTATION_APPROVE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="SALES_QUOTATION_APPROVED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="sent",
                    to_step="rejected",
                    name="Reject Quotation",
                    feature_code="SALES_QUOTATION_APPROVE",
                    permission_action="approve",
                    requires_note=True,
                    is_approval=True,
                    event_code="SALES_QUOTATION_REJECTED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="approved",
                    to_step="converted",
                    name="Convert to Enterprise Order",
                    feature_code="SALES_QUOTATION_CONVERT",
                    permission_action="approve",
                    event_code="SALES_QUOTATION_CONVERTED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="draft",
                    to_step="cancelled",
                    name="Cancel Quotation",
                    feature_code="SALES_QUOTATION_EDIT",
                    permission_action="delete",
                    requires_note=True,
                    event_code="SALES_QUOTATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="rejected",
                    to_step="cancelled",
                    name="Cancel Quotation",
                    feature_code="SALES_QUOTATION_EDIT",
                    permission_action="delete",
                    requires_note=True,
                    event_code="SALES_QUOTATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="sent",
                    to_step="cancelled",
                    name="Cancel Quotation",
                    feature_code="SALES_QUOTATION_APPROVE",
                    permission_action="approve",
                    requires_note=True,
                    event_code="SALES_QUOTATION_CANCELLED",
                    event_level="WARNING",
                ),
            ),
        ),

        # =================================================
        # FURNITURE PRODUCTION
        # =================================================

        "FURNITURE_PRODUCTION": WorkflowDefinition(
            code="FURNITURE_PRODUCTION",
            name="Furniture Production Workflow",

            steps=(
                WorkflowStep(
                    "QUOTATION",
                    "Costing / Quotation",
                    1,
                    color="secondary",
                ),
                WorkflowStep(
                    "APPROVED",
                    "Approved",
                    2,
                    requires_approval=True,
                    color="success",
                ),
                WorkflowStep(
                    "ORDER_CONFIRMED",
                    "Order Confirmed",
                    3,
                    color="primary",
                ),
                WorkflowStep(
                    "MATERIAL_RESERVED",
                    "Material Reserved",
                    4,
                    color="info",
                ),
                WorkflowStep(
                    "IN_PRODUCTION",
                    "In Production",
                    5,
                    color="warning",
                ),
                WorkflowStep(
                    "QUALITY_CHECK",
                    "Quality Check",
                    6,
                    color="info",
                ),
                WorkflowStep(
                    "FINISHED_GOODS",
                    "Finished Goods",
                    7,
                    color="success",
                ),
                WorkflowStep(
                    "DELIVERED",
                    "Delivered",
                    8,
                    is_terminal=True,
                    color="success",
                ),
                WorkflowStep(
                    "CANCELLED",
                    "Cancelled",
                    9,
                    is_terminal=True,
                    color="danger",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    "QUOTATION",
                    "APPROVED",
                    name="Approve Cost Estimate",
                    feature_code="FURNITURE_COSTING_APPROVE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="FURNITURE_COSTING_APPROVED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    "APPROVED",
                    "ORDER_CONFIRMED",
                    name="Confirm Order",
                    feature_code="FURNITURE_ORDER_CONFIRM",
                    permission_action="approve",
                    event_code="FURNITURE_ORDER_CONFIRMED",
                ),
                WorkflowTransitionDefinition(
                    "ORDER_CONFIRMED",
                    "MATERIAL_RESERVED",
                    name="Reserve Materials",
                    feature_code="FURNITURE_MATERIAL_RESERVE",
                    permission_action="edit",
                    event_code="FURNITURE_MATERIAL_RESERVED",
                ),
                WorkflowTransitionDefinition(
                    "MATERIAL_RESERVED",
                    "IN_PRODUCTION",
                    name="Start Production",
                    feature_code="FURNITURE_PRODUCTION_START",
                    permission_action="edit",
                    event_code="FURNITURE_PRODUCTION_STARTED",
                ),
                WorkflowTransitionDefinition(
                    "IN_PRODUCTION",
                    "QUALITY_CHECK",
                    name="Send to Quality Check",
                    feature_code="FURNITURE_QUALITY_CHECK",
                    permission_action="edit",
                    event_code="FURNITURE_QUALITY_CHECK_STARTED",
                ),
                WorkflowTransitionDefinition(
                    "QUALITY_CHECK",
                    "FINISHED_GOODS",
                    name="Approve Finished Goods",
                    feature_code="FURNITURE_QUALITY_CHECK",
                    permission_action="approve",
                    event_code="FURNITURE_FINISHED_GOODS_APPROVED",
                ),
                WorkflowTransitionDefinition(
                    "FINISHED_GOODS",
                    "DELIVERED",
                    name="Deliver",
                    feature_code="FURNITURE_DELIVERY",
                    permission_action="edit",
                    event_code="FURNITURE_DELIVERED",
                    event_level="SUCCESS",
                ),
            ),
        ),

        # =================================================
        # CONSTRUCTION PROJECT
        # =================================================

        "CONSTRUCTION_PROJECT": WorkflowDefinition(
            code="CONSTRUCTION_PROJECT",
            name="Construction Project Workflow",

            steps=(
                WorkflowStep("PLANNING", "Planning", 1),
                WorkflowStep(
                    "BUDGET_APPROVAL",
                    "Budget Approval",
                    2,
                    requires_approval=True,
                    color="warning",
                ),
                WorkflowStep("PROCUREMENT", "Procurement", 3),
                WorkflowStep("EXECUTION", "Execution", 4),
                WorkflowStep("INSPECTION", "Inspection", 5),
                WorkflowStep(
                    "COMPLETED",
                    "Completed",
                    6,
                    is_terminal=True,
                    color="success",
                ),
                WorkflowStep(
                    "CANCELLED",
                    "Cancelled",
                    7,
                    is_terminal=True,
                    color="danger",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    "PLANNING",
                    "BUDGET_APPROVAL",
                    name="Submit Budget",
                    feature_code="CONSTRUCTION_BUDGET_SUBMIT",
                    permission_action="edit",
                    event_code="CONSTRUCTION_BUDGET_SUBMITTED",
                ),
                WorkflowTransitionDefinition(
                    "BUDGET_APPROVAL",
                    "PROCUREMENT",
                    name="Approve Budget",
                    feature_code="CONSTRUCTION_BUDGET_APPROVE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="CONSTRUCTION_BUDGET_APPROVED",
                ),
                WorkflowTransitionDefinition(
                    "PROCUREMENT",
                    "EXECUTION",
                    name="Start Execution",
                    feature_code="CONSTRUCTION_EXECUTION_START",
                    permission_action="edit",
                    event_code="CONSTRUCTION_EXECUTION_STARTED",
                ),
                WorkflowTransitionDefinition(
                    "EXECUTION",
                    "INSPECTION",
                    name="Request Inspection",
                    feature_code="CONSTRUCTION_INSPECTION",
                    permission_action="edit",
                    event_code="CONSTRUCTION_INSPECTION_REQUESTED",
                ),
                WorkflowTransitionDefinition(
                    "INSPECTION",
                    "COMPLETED",
                    name="Complete Project",
                    feature_code="CONSTRUCTION_COMPLETE",
                    permission_action="approve",
                    event_code="CONSTRUCTION_PROJECT_COMPLETED",
                    event_level="SUCCESS",
                ),
            ),
        ),

        # =================================================
        # FINANCE PAYMENT
        # =================================================

        "FINANCE_PAYMENT": WorkflowDefinition(
            code="FINANCE_PAYMENT",
            name="Finance Payment Workflow",

            steps=(
                WorkflowStep("DRAFT", "Draft", 1),
                WorkflowStep("SUBMITTED", "Submitted", 2),
                WorkflowStep("FINANCE_REVIEW", "Finance Review", 3),
                WorkflowStep(
                    "APPROVED",
                    "Approved",
                    4,
                    requires_approval=True,
                    color="success",
                ),
                WorkflowStep(
                    "REJECTED",
                    "Rejected",
                    5,
                    is_terminal=True,
                    color="danger",
                ),
                WorkflowStep(
                    "PAID",
                    "Paid",
                    6,
                    is_terminal=True,
                    color="success",
                ),
                WorkflowStep(
                    "CANCELLED",
                    "Cancelled",
                    7,
                    is_terminal=True,
                    color="danger",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    "DRAFT",
                    "SUBMITTED",
                    name="Submit Payment",
                    feature_code="FINANCE_PAYMENT_SUBMIT",
                    permission_action="edit",
                    event_code="FINANCE_PAYMENT_SUBMITTED",
                ),
                WorkflowTransitionDefinition(
                    "SUBMITTED",
                    "FINANCE_REVIEW",
                    name="Start Finance Review",
                    feature_code="FINANCE_PAYMENT_REVIEW",
                    permission_action="edit",
                    event_code="FINANCE_PAYMENT_REVIEW_STARTED",
                ),
                WorkflowTransitionDefinition(
                    "FINANCE_REVIEW",
                    "APPROVED",
                    name="Approve Payment",
                    feature_code="FINANCE_PAYMENT_APPROVE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="FINANCE_PAYMENT_APPROVED",
                ),
                WorkflowTransitionDefinition(
                    "FINANCE_REVIEW",
                    "REJECTED",
                    name="Reject Payment",
                    feature_code="FINANCE_PAYMENT_APPROVE",
                    permission_action="approve",
                    requires_note=True,
                    is_approval=True,
                    event_code="FINANCE_PAYMENT_REJECTED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    "APPROVED",
                    "PAID",
                    name="Mark Paid",
                    feature_code="FINANCE_PAYMENT_EXECUTE",
                    permission_action="approve",
                    event_code="FINANCE_PAYMENT_PAID",
                    event_level="SUCCESS",
                ),
            ),
        ),

        # =================================================
        # AGRICULTURE / POULTRY OPERATION
        # =================================================

        "AGRICULTURE_OPERATION": WorkflowDefinition(
            code="AGRICULTURE_OPERATION",
            name="Agriculture / Poultry Operation Workflow",

            steps=(
                WorkflowStep(
                    code="DRAFT",
                    name="Draft",
                    order=1,
                    color="secondary",
                    icon="fas fa-file-alt",
                ),
                WorkflowStep(
                    code="PENDING",
                    name="Pending Approval",
                    order=2,
                    color="warning",
                    icon="fas fa-paper-plane",
                ),
                WorkflowStep(
                    code="APPROVED",
                    name="Approved",
                    order=3,
                    requires_approval=True,
                    color="success",
                    icon="fas fa-check-circle",
                ),
                WorkflowStep(
                    code="ACTIVE",
                    name="Active",
                    order=4,
                    color="primary",
                    icon="fas fa-play-circle",
                ),
                WorkflowStep(
                    code="ON_HOLD",
                    name="On Hold",
                    order=5,
                    color="warning",
                    icon="fas fa-pause-circle",
                ),
                WorkflowStep(
                    code="COMPLETED",
                    name="Completed",
                    order=6,
                    is_terminal=True,
                    color="success",
                    icon="fas fa-check-double",
                ),
                WorkflowStep(
                    code="CANCELLED",
                    name="Cancelled",
                    order=7,
                    is_terminal=True,
                    color="danger",
                    icon="fas fa-ban",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    from_step="DRAFT",
                    to_step="PENDING",
                    name="Submit for Approval",
                    feature_code="AGRICULTURE_OPERATION_SUBMIT",
                    permission_action="edit",
                    event_code="AGRICULTURE_OPERATION_SUBMITTED",
                ),
                WorkflowTransitionDefinition(
                    from_step="PENDING",
                    to_step="APPROVED",
                    name="Approve Operation",
                    feature_code="AGRICULTURE_OPERATION_APPROVE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="AGRICULTURE_OPERATION_APPROVED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="PENDING",
                    to_step="DRAFT",
                    name="Return for Correction",
                    feature_code="AGRICULTURE_OPERATION_APPROVE",
                    permission_action="approve",
                    requires_note=True,
                    is_approval=True,
                    event_code="AGRICULTURE_OPERATION_RETURNED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="APPROVED",
                    to_step="ACTIVE",
                    name="Start Operation",
                    feature_code="AGRICULTURE_OPERATION_START",
                    permission_action="edit",
                    event_code="AGRICULTURE_OPERATION_STARTED",
                ),
                WorkflowTransitionDefinition(
                    from_step="ACTIVE",
                    to_step="ON_HOLD",
                    name="Place on Hold",
                    feature_code="AGRICULTURE_OPERATION_HOLD",
                    permission_action="edit",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_HELD",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="ON_HOLD",
                    to_step="ACTIVE",
                    name="Resume Operation",
                    feature_code="AGRICULTURE_OPERATION_RESUME",
                    permission_action="edit",
                    event_code="AGRICULTURE_OPERATION_RESUMED",
                ),
                WorkflowTransitionDefinition(
                    from_step="ACTIVE",
                    to_step="COMPLETED",
                    name="Complete Operation",
                    feature_code="AGRICULTURE_OPERATION_COMPLETE",
                    permission_action="approve",
                    is_approval=True,
                    event_code="AGRICULTURE_OPERATION_COMPLETED",
                    event_level="SUCCESS",
                ),
                WorkflowTransitionDefinition(
                    from_step="DRAFT",
                    to_step="CANCELLED",
                    name="Cancel Operation",
                    feature_code="AGRICULTURE_OPERATION_CANCEL",
                    permission_action="delete",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="PENDING",
                    to_step="CANCELLED",
                    name="Cancel Operation",
                    feature_code="AGRICULTURE_OPERATION_CANCEL",
                    permission_action="delete",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="APPROVED",
                    to_step="CANCELLED",
                    name="Cancel Operation",
                    feature_code="AGRICULTURE_OPERATION_CANCEL",
                    permission_action="delete",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="ACTIVE",
                    to_step="CANCELLED",
                    name="Cancel Operation",
                    feature_code="AGRICULTURE_OPERATION_CANCEL",
                    permission_action="delete",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_CANCELLED",
                    event_level="WARNING",
                ),
                WorkflowTransitionDefinition(
                    from_step="ON_HOLD",
                    to_step="CANCELLED",
                    name="Cancel Operation",
                    feature_code="AGRICULTURE_OPERATION_CANCEL",
                    permission_action="delete",
                    requires_note=True,
                    event_code="AGRICULTURE_OPERATION_CANCELLED",
                    event_level="WARNING",
                ),
            ),
        ),


        # =================================================
        # MARKETPLACE ORDER
        # =================================================

        "MARKETPLACE_ORDER": WorkflowDefinition(
            code="MARKETPLACE_ORDER",
            name="Marketplace Order Workflow",

            steps=(
                WorkflowStep("PLACED", "Placed", 1),
                WorkflowStep("CONFIRMED", "Confirmed", 2),
                WorkflowStep("PROCESSING", "Processing", 3),
                WorkflowStep(
                    "READY_FOR_DELIVERY",
                    "Ready for Delivery",
                    4,
                ),
                WorkflowStep(
                    "DELIVERED",
                    "Delivered",
                    5,
                    is_terminal=True,
                    color="success",
                ),
                WorkflowStep(
                    "CANCELLED",
                    "Cancelled",
                    6,
                    is_terminal=True,
                    color="danger",
                ),
            ),

            transitions=(
                WorkflowTransitionDefinition(
                    "PLACED",
                    "CONFIRMED",
                    name="Confirm Order",
                    feature_code="MARKETPLACE_ORDER_CONFIRM",
                    permission_action="approve",
                    event_code="MARKETPLACE_ORDER_CONFIRMED",
                ),
                WorkflowTransitionDefinition(
                    "CONFIRMED",
                    "PROCESSING",
                    name="Start Processing",
                    feature_code="MARKETPLACE_ORDER_PROCESS",
                    permission_action="edit",
                    event_code="MARKETPLACE_ORDER_PROCESSING",
                ),
                WorkflowTransitionDefinition(
                    "PROCESSING",
                    "READY_FOR_DELIVERY",
                    name="Mark Ready",
                    feature_code="MARKETPLACE_ORDER_DELIVERY",
                    permission_action="edit",
                    event_code="MARKETPLACE_ORDER_READY",
                ),
                WorkflowTransitionDefinition(
                    "READY_FOR_DELIVERY",
                    "DELIVERED",
                    name="Deliver",
                    feature_code="MARKETPLACE_ORDER_DELIVERY",
                    permission_action="edit",
                    event_code="MARKETPLACE_ORDER_DELIVERED",
                    event_level="SUCCESS",
                ),
            ),
        ),
    }

    # =====================================================
    # REGISTRY ACCESS
    # =====================================================

    @classmethod
    def get_definition(cls, workflow_code):
        """
        Return a workflow definition.

        Unknown workflows fall back to GENERIC for backward
        compatibility.
        """

        return cls.WORKFLOWS.get(
            workflow_code,
            cls.WORKFLOWS["GENERIC"],
        )

    @classmethod
    def get_workflow(cls, workflow_code):
        """
        Backward-compatible method.

        Previously returned a list of WorkflowStep objects.
        """

        return list(
            cls.get_definition(
                workflow_code
            ).steps
        )

    @classmethod
    def get_steps(cls, workflow_code):
        return cls.get_workflow(
            workflow_code
        )

    @classmethod
    def get_transitions(cls, workflow_code):
        return list(
            cls.get_definition(
                workflow_code
            ).transitions
        )

    # =====================================================
    # STEP HELPERS
    # =====================================================

    @classmethod
    def get_first_step(cls, workflow_code):
        steps = cls.get_steps(
            workflow_code
        )

        return steps[0]

    @classmethod
    def get_step(
        cls,
        workflow_code,
        step_code,
    ):
        for step in cls.get_steps(
            workflow_code
        ):
            if step.code == step_code:
                return step

        return None

    @classmethod
    def requires_approval(
        cls,
        workflow_code,
        step_code,
    ):
        step = cls.get_step(
            workflow_code,
            step_code,
        )

        return bool(
            step
            and step.requires_approval
        )

    @classmethod
    def is_terminal(
        cls,
        workflow_code,
        step_code,
    ):
        step = cls.get_step(
            workflow_code,
            step_code,
        )

        return bool(
            step
            and step.is_terminal
        )

    # =====================================================
    # TRANSITION HELPERS
    # =====================================================

    @classmethod
    def get_transition(
        cls,
        workflow_code,
        from_step,
        to_step,
    ):
        for transition in cls.get_transitions(
            workflow_code
        ):
            if (
                transition.from_step == from_step
                and transition.to_step == to_step
            ):
                return transition

        return None

    @classmethod
    def can_move_to(
        cls,
        workflow_code,
        current_step_code,
        next_step_code,
    ):
        """
        Return True when an explicit transition exists.
        """

        return (
            cls.get_transition(
                workflow_code,
                current_step_code,
                next_step_code,
            )
            is not None
        )

    @classmethod
    def get_available_transitions(
        cls,
        workflow_code,
        current_step_code,
    ):
        """
        Return every action available from the current step.
        """

        return [
            transition
            for transition in cls.get_transitions(
                workflow_code
            )
            if transition.from_step
            == current_step_code
        ]

    @classmethod
    def get_next_step(
        cls,
        workflow_code,
        current_step_code,
    ):
        """
        Backward-compatible linear helper.

        For workflows with multiple possible transitions, it returns
        the first registered transition. New code should preferably
        use get_available_transitions() or get_transition().
        """

        transitions = cls.get_available_transitions(
            workflow_code,
            current_step_code,
        )

        if transitions:
            return cls.get_step(
                workflow_code,
                transitions[0].to_step,
            )

        current_step = cls.get_step(
            workflow_code,
            current_step_code,
        )

        if current_step:
            return current_step

        return cls.get_first_step(
            workflow_code
        )

    # =====================================================
    # UI / ACTION HELPERS
    # =====================================================

    @classmethod
    def get_action_map(
        cls,
        workflow_code,
        current_step_code,
    ):
        """
        Return transitions as a dictionary useful for views/templates.
        """

        return {
            transition.to_step: transition
            for transition in (
                cls.get_available_transitions(
                    workflow_code,
                    current_step_code,
                )
            )
        }