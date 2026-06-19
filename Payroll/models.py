from django.db import models
from decimal import Decimal
from Employee.models import *


class Payroll(models.Model):

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    month = models.DateField()  # use first day of month
    basic_salary = models.DecimalField(max_digits=15, decimal_places=2)

    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    gross_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_overtime(self):
        return self.overtime_hours * self.overtime_rate

    def save(self, *args, **kwargs):

        overtime_amount = self.calculate_overtime()

        self.gross_salary = self.basic_salary + overtime_amount
        self.net_salary = self.gross_salary - self.deductions

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee} - {self.month}"