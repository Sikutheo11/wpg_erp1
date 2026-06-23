from django.db import models
from django.contrib.auth.models import Group


# ==========================================
# SYSTEM MODULES
# ==========================================

class Module(models.Model):

    name = models.CharField(
        max_length=100
    )

    icon = models.CharField(
        max_length=50,
        blank=True
    )

    url_name = models.CharField(
        max_length=100
    )

    permission = models.CharField(
        max_length=150
    )

    is_active = models.BooleanField(
        default=True
    )


    def __str__(self):

        return self.name




# ==========================================
# ROLE MODULE ACCESS
# ==========================================


class RoleModule(models.Model):

    role = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="modules"
    )


    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="roles"
    )


    can_view = models.BooleanField(
        default=True
    )


    can_add = models.BooleanField(
        default=False
    )


    can_edit = models.BooleanField(
        default=False
    )


    can_delete = models.BooleanField(
        default=False
    )



    class Meta:

        unique_together = (
            "role",
            "module",
        )



    def __str__(self):

        return (
            f"{self.role.name}"
            f" - "
            f"{self.module.name}"
        )