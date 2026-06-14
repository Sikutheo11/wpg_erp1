from django.db import models
from django.db.models import Sum
from accounts.models import User
from django.utils import timezone
from Employee.models import *
from inventory.models import *
from sales.models import Sale

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('mobile', 'Mobile Money'),
    )

    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=50, blank=True, null=True)

    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Income(models.Model):
    INCOME_TYPES = (
        ('sales', 'Sales'),
        ('service', 'Service'),
        ('construction', 'Construction'),
        ('other', 'Other'),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    title = models.CharField(max_length=200, blank=True, null=True)
    income_type = models.CharField(max_length=50, choices=INCOME_TYPES, default='other')

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()

    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or "Income"

class Expense(models.Model):
    EXPENSE_TYPES = (
        ('salary', 'Salary'),
        ('rent', 'Rent'),
        ('utilities', 'Utilities'),
        ('transport', 'Transport'),
        ('raw_material', 'Raw Material'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE,null=True, blank=True)

    title = models.CharField(max_length=200, blank=True, null=True)
    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES)

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or "Expense"

    def save(self, *args, **kwargs):
        if not self.account:
            self.account = Account.objects.first()  # or a specific one
        super().save(*args, **kwargs)


class Receivable(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    invoice_number = models.CharField(max_length=50)

    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    due_date = models.DateField()

    STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def save(self, *args, **kwargs):
        if self.amount_paid == 0:
            self.status = 'unpaid'
        elif self.amount_paid < self.total_amount:
            self.status = 'partial'
        else:
            self.status = 'paid'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number

class Payable(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100)

    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    due_date = models.DateField()

    STATUS_CHOICES = (
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    def save(self, *args, **kwargs):
        if self.amount_paid == 0:
            self.status = 'unpaid'
        elif self.amount_paid < self.total_amount:
            self.status = 'partial'
        else:
            self.status = 'paid'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.reference


class Payment(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('bank', 'Bank'),
    )

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    receivable = models.ForeignKey(Receivable, on_delete=models.SET_NULL, null=True, blank=True)
    payable = models.ForeignKey(Payable, on_delete=models.SET_NULL, null=True, blank=True)

    date = models.DateField(auto_now_add=True)

    notes = models.TextField(blank=True)

    def clean(self):
        if not self.receivable and not self.payable:
            raise ValidationError("Payment must be linked to receivable or payable")

        if self.receivable and self.payable:
            raise ValidationError("Payment cannot be both receivable and payable")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.receivable:
            self.receivable.amount_paid += self.amount
            self.receivable.save()

        if self.payable:
            self.payable.amount_paid += self.amount
            self.payable.save()

    def __str__(self):
        return f"{self.amount} - {self.method}"


def calculate_financial_summary(start_date, end_date):

    income = Income.objects.filter(date__range=(start_date, end_date)).aggregate(
        total=Sum('amount')
    )['total'] or 0

    expenses = Expense.objects.filter(date__range=(start_date, end_date)).aggregate(
        total=Sum('amount')
    )['total'] or 0

    receivable = AccountsReceivable.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    payable = AccountsPayable.objects.aggregate(total=Sum('amount_paid'))['total'] or 0

    profit = (income + receivable) - (expenses + payable)

    return {
        "income": income,
        "expenses": expenses,
        "receivables": receivable,
        "payables": payable,
        "profit": profit
    }

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