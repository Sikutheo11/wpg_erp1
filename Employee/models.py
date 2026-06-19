from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from django.db.models import Max
from django.contrib.auth.models import Group
import random
import string
from accounts.models import User


# =========================
# DEPARTMENT
# =========================
class Department(models.Model):

    DEPARTMENT_CHOICES = (
        ('furniture', 'Furniture'),
        ('machinist', 'Machinist'),
        ('construction', 'Construction'),
        ('finance', 'Finance'),
        ('operations', 'Operations'),
        ('sales', 'Sales'),
        ('hr', 'Human Resource'),
        ('procurement', 'Procurement'),
        ('warehouse', 'Warehouse'),
    )

    code = models.CharField(max_length=20, unique=True, blank=True)

    name = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        unique=True
    )

    description = models.TextField(blank=True, null=True)

    manager = models.ForeignKey(User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.name[:3].upper()
        super().save(*args, **kwargs)


# =========================
# POSITION
# =========================
class Position(models.Model):
    POSITION_CHOICES = (
        ('manager', 'Manager'),
        ('worker', 'Worker'),
        ('cashier', 'Cashier'),
        ('salesperson', 'Sales Person'),
        ('chief_operation_manager', 'Chief Operation Manager'),
    )

    title = models.CharField(max_length=100, choices=POSITION_CHOICES)

    def __str__(self):
        return self.get_title_display()


# =========================
# EMPLOYEE
# =========================
class Employee(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True,blank=True)
    employee_code = models.CharField(max_length=20, unique=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hire_date = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=30)
    emergency_contact = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_employee_code(self):
        last_id = Employee.objects.aggregate(Max('id'))['id__max'] or 0
        suffix = ''.join(random.choices(string.ascii_uppercase, k=1))
        return f"WPG{last_id + 1:05d}{suffix}"

    def save(self, *args, **kwargs):
        if not self.employee_code:
            self.employee_code = self.generate_employee_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


# =========================
# ATTENDANCE
# =========================
class Attendance(models.Model):

    STATUS_CHOICES = (
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        ('half_day', 'Half Day'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    date = models.DateField()

    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ('employee', 'date')

    def __str__(self):
        return f"{self.employee} - {self.date}"

    def save(self, *args, **kwargs):
        if self.check_in and self.check_out:
            today_in = datetime.combine(self.date, self.check_in)
            today_out = datetime.combine(self.date, self.check_out)

            diff = today_out - today_in
            total_minutes = diff.total_seconds() / 60

            hours = int(total_minutes // 60)
            minutes = int(total_minutes % 60)

            self.hours_worked = round(hours + (minutes / 60), 2)
        else:
            self.hours_worked = 0

        super().save(*args, **kwargs)


# =========================
# LEAVE
# =========================
class Leave(models.Model):

    LEAVE_TYPES = (
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('other', 'Other'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)

    start_date = models.DateField()
    end_date = models.DateField()

    reason = models.TextField(blank=True)

    approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type}"

# Employee/models.py

class Contact(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.name