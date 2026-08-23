from django.db import models
from django.conf import settings
from django.contrib.auth.models import Group


# ==========================================
# SYSTEM MODULES
# ==========================================

class Module(models.Model):
    name = models.CharField(max_length=100)

    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    icon = models.CharField(
        max_length=50,
        blank=True
    )

    url_name = models.CharField(
        max_length=100
    )

    permission = models.CharField(
        max_length=150,
        blank=True
    )

    order = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class RoleModule(models.Model):
    role = models.ForeignKey(
        "auth.Group",
        on_delete=models.CASCADE,
        related_name="core_modules"
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="roles"
    )

    can_view = models.BooleanField(default=True)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)

    can_approve = models.BooleanField(
        default=False
    )

    class Meta:
        unique_together = ("role", "module")

    def __str__(self):
        return f"{self.role.name} - {self.module.name}"


# ==========================================
# DASHBOARD CARDS
# ==========================================

class DashboardCard(models.Model):
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="dashboard_cards", null=True, blank=True
    )

    title = models.CharField(max_length=100)

    code = models.CharField(
        max_length=100,
        unique=True
    )

    icon = models.CharField(
        max_length=50,
        blank=True
    )

    color = models.CharField(
        max_length=30,
        default="primary"
    )

    order = models.PositiveIntegerField(
        default=0
    )

    is_active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return f"{self.module.name} - {self.title}"


# ==========================================
# AUDIT LOG
# ==========================================


class AuditLog(models.Model):
    ACTIONS = (
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("APPROVE", "Approve"),
        ("REJECT", "Reject"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("VIEW", "View"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=20,
        choices=ACTIONS
    )

    app_label = models.CharField(
        max_length=100
    )

    model_name = models.CharField(
        max_length=100
    )

    object_id = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    old_data = models.JSONField(
        null=True,
        blank=True
    )

    new_data = models.JSONField(
        null=True,
        blank=True
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("view_reports", "Can access the reports centre"),
            ("view_executivereport", "Can view executive reports"),
        ]

    def __str__(self):
        return f"{self.action} - {self.app_label}.{self.model_name}"


# ==========================================
# NOTIFICATIONS
# ==========================================

class Notification(models.Model):
    LEVELS = (
        ("INFO", "Info"),
        ("SUCCESS", "Success"),
        ("WARNING", "Warning"),
        ("DANGER", "Danger"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=150
    )

    message = models.TextField()

    level = models.CharField(
        max_length=20,
        choices=LEVELS,
        default="INFO"
    )

    url = models.CharField(
        max_length=255,
        blank=True
    )

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


# ==========================================
# WORKFLOW TRANSITIONS
# ==========================================

class WorkflowTransition(models.Model):

    workflow_code = models.CharField(
        max_length=100
    )

    object_app = models.CharField(
        max_length=100
    )

    object_model = models.CharField(
        max_length=100
    )

    object_id = models.CharField(
        max_length=100
    )

    from_step = models.CharField(
        max_length=100,
        blank=True
    )

    to_step = models.CharField(
        max_length=100
    )

    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    note = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.workflow_code}: {self.from_step} → {self.to_step}"

# ==========================================
# BUSINESS UNITS
# ==========================================

class BusinessUnit(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)

    description = models.TextField(blank=True)

    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ==========================================
# ENTERPRISE ENGINES
# ==========================================

class EnterpriseEngine(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


# ==========================================
# MODULE FEATURES
# ==========================================

class Feature(models.Model):

    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="features",
        null=True,
        blank=True
    )

    engine = models.ForeignKey(
        EnterpriseEngine,
        on_delete=models.CASCADE,
        related_name="features",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)

    code = models.CharField(
        max_length=100,
        unique=True
    )

    url_name = models.CharField(
        max_length=150,
        blank=True
    )

    icon = models.CharField(
        max_length=50,
        blank=True
    )

    view_permission = models.CharField(
        max_length=150,
        blank=True,
        help_text="Django permission required to see and open this feature.",
    )
    add_permission = models.CharField(
        max_length=150,
        blank=True,
        help_text="Django permission required to create records.",
    )
    change_permission = models.CharField(
        max_length=150,
        blank=True,
        help_text="Django permission required to edit records.",
    )
    delete_permission = models.CharField(
        max_length=150,
        blank=True,
        help_text="Django permission required to delete records.",
    )
    approve_permission = models.CharField(
        max_length=150,
        blank=True,
        help_text="Custom Django permission required to approve records.",
    )

    order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        owner = self.business_unit or self.engine
        return f"{owner} - {self.name}"
        
# ==========================================
# ROLE FEATURE PERMISSIONS
# ==========================================

class RoleFeature(models.Model):
    role = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="features"
    )

    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="roles"
    )

    can_view = models.BooleanField(default=True)
    can_add = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)

    class Meta:
        unique_together = ("role", "feature")

    def __str__(self):
        return f"{self.role.name} - {self.feature.name}"

# ==========================================
# KPI WIDGETS
# Enterprise dashboard widgets
# ==========================================

class KPIWidget(models.Model):

    WIDGET_TYPES = (
        ("NUMBER", "Number"),
        ("MONEY", "Money"),
        ("PERCENT", "Percent"),
        ("CHART", "Chart"),
        ("TABLE", "Table"),
        ("ALERT", "Alert"),
    )

    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="kpi_widgets",
        null=True,
        blank=True
    )

    engine = models.ForeignKey(
        EnterpriseEngine,
        on_delete=models.CASCADE,
        related_name="kpi_widgets",
        null=True,
        blank=True
    )

    title = models.CharField(max_length=120)

    code = models.CharField(
        max_length=120,
        unique=True
    )

    widget_type = models.CharField(
        max_length=20,
        choices=WIDGET_TYPES,
        default="NUMBER"
    )

    data_source = models.CharField(
        max_length=150,
        blank=True,
        help_text="Example: finance.net_profit or furniture.active_jobs"
    )

    value_key = models.CharField(
        max_length=100,
        blank=True,
        help_text="Key returned by dashboard service"
    )

    icon = models.CharField(
        max_length=50,
        blank=True
    )

    color = models.CharField(
        max_length=30,
        default="primary"
    )

    order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        owner = self.business_unit or self.engine
        return f"{owner} - {self.title}"

# ==========================================
# APPROVAL REQUESTS
# ==========================================

class ApprovalRequest(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    workflow_code = models.CharField(max_length=100)

    object_app = models.CharField(max_length=100)
    object_model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)

    from_step = models.CharField(max_length=100, blank=True)
    to_step = models.CharField(max_length=100)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_requests_made"
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_requests_approved"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    reason = models.TextField(blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.object_app}.{self.object_model} → {self.to_step} ({self.status})"
