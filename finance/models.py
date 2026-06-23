from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

from Employee.models import Employee
from inventory.models import Supplier
from sales.models import Sale
from accounts.models import User



# =====================================================
# ACCOUNT
# =====================================================

class Account(models.Model):

    ACCOUNT_TYPES = (
        ('cash','Cash'),
        ('bank','Bank'),
        ('mobile','Mobile Money'),
    )


    name = models.CharField(max_length=100)

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPES
    )

    account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )


    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.name




# =====================================================
# TRANSACTION
# =====================================================

class Transaction(models.Model):

    TYPES = (
        ('income','Income'),
        ('expense','Expense'),
    )


    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions"
    )


    transaction_type=models.CharField(
        max_length=20,
        choices=TYPES
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    description=models.CharField(
        max_length=255
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.description





# =====================================================
# INCOME
# =====================================================

class Income(models.Model):


    INCOME_TYPES = (

        ('sales','Sales'),
        ('construction','Construction'),
        ('furniture','Furniture'),
        ('service','Service'),
        ('other','Other'),

    )


    account=models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    title=models.CharField(
        max_length=200,
        blank=True,
        null=True
    )


    income_type=models.CharField(
        max_length=50,
        choices=INCOME_TYPES,
        default="other"
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    sale=models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        is_new=self.pk is None

        super().save(*args,**kwargs)


        if is_new and self.account:

            self.account.balance += self.amount
            self.account.save()


            Transaction.objects.create(
                account=self.account,
                transaction_type="income",
                amount=self.amount,
                description=self.title or "Income"
            )


    def __str__(self):
        return self.title or "Income"





# =====================================================
# EXPENSE
# =====================================================

class Expense(models.Model):


    EXPENSE_TYPES=(

        ('salary','Salary'),
        ('rent','Rent'),
        ('transport','Transport'),
        ('raw_material','Raw Material'),
        ('maintenance','Maintenance'),
        ('other','Other'),

    )


    account=models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    title=models.CharField(
        max_length=200,
        blank=True,
        null=True
    )


    expense_type=models.CharField(
        max_length=50,
        choices=EXPENSE_TYPES
    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    supplier=models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        default=timezone.now
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        is_new=self.pk is None

        super().save(*args,**kwargs)


        if is_new and self.account:

            self.account.balance -= self.amount
            self.account.save()


            Transaction.objects.create(
                account=self.account,
                transaction_type="expense",
                amount=self.amount,
                description=self.title or "Expense"
            )



    def __str__(self):
        return self.title or "Expense"





# =====================================================
# RECEIVABLE (CUSTOMER DEBT)
# =====================================================

class Receivable(models.Model):


    customer=models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )


    invoice_number=models.CharField(
        max_length=50
    )


    total_amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    amount_paid=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    due_date=models.DateField()



    STATUS=(

        ('unpaid','Unpaid'),
        ('partial','Partial'),
        ('paid','Paid'),
        ('overdue','Overdue'),

    )


    status=models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid"
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )


    @property
    def balance(self):

        return self.total_amount-self.amount_paid



    def save(self,*args,**kwargs):

        if self.amount_paid==0:
            self.status="unpaid"

        elif self.amount_paid < self.total_amount:
            self.status="partial"

        else:
            self.status="paid"


        super().save(*args,**kwargs)





# =====================================================
# PAYABLE (SUPPLIER DEBT)
# =====================================================

class Payable(models.Model):


    supplier=models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE
    )


    reference=models.CharField(
        max_length=100
    )


    total_amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    amount_paid=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    due_date=models.DateField()


    STATUS=(

        ('unpaid','Unpaid'),
        ('partial','Partial'),
        ('paid','Paid'),

    )


    status=models.CharField(
        max_length=20,
        choices=STATUS,
        default="unpaid"
    )



    created_at=models.DateTimeField(
        auto_now_add=True
    )



    @property
    def balance(self):

        return self.total_amount-self.amount_paid



    def save(self,*args,**kwargs):

        if self.amount_paid==0:
            self.status="unpaid"

        elif self.amount_paid < self.total_amount:
            self.status="partial"

        else:
            self.status="paid"


        super().save(*args,**kwargs)





# =====================================================
# PAYMENT
# =====================================================

class Payment(models.Model):


    METHODS=(

        ('cash','Cash'),
        ('bank','Bank'),
        ('mobile_money','Mobile Money'),

    )


    amount=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    method=models.CharField(
        max_length=30,
        choices=METHODS
    )


    receivable=models.ForeignKey(
        Receivable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    payable=models.ForeignKey(
        Payable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


    date=models.DateField(
        auto_now_add=True
    )


    notes=models.TextField(
        blank=True
    )


    def clean(self):

        if not self.receivable and not self.payable:

            raise ValidationError(
                "Payment must belong to receivable or payable"
            )


        if self.receivable and self.payable:

            raise ValidationError(
                "Payment cannot be both"
            )



    def save(self,*args,**kwargs):

        self.clean()

        super().save(*args,**kwargs)


        if self.receivable:

            self.receivable.amount_paid += self.amount
            self.receivable.save()



        if self.payable:

            self.payable.amount_paid += self.amount
            self.payable.save()




# =====================================================
# PAYROLL
# =====================================================

class Payroll(models.Model):


    employee=models.ForeignKey(
        Employee,
        on_delete=models.CASCADE
    )


    month=models.DateField()



    basic_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2
    )


    overtime_hours=models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )


    overtime_rate=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )


    deductions=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    gross_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    net_salary=models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )


    created_at=models.DateTimeField(
        auto_now_add=True
    )



    def save(self,*args,**kwargs):

        overtime=self.overtime_hours*self.overtime_rate

        self.gross_salary=self.basic_salary+overtime

        self.net_salary=self.gross_salary-self.deductions


        super().save(*args,**kwargs)



    def __str__(self):

        return f"{self.employee}-{self.month}"





# =====================================================
# FINANCIAL REPORT
# =====================================================

def calculate_financial_summary(start_date,end_date):


    income=Income.objects.filter(
        date__range=(start_date,end_date)
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0



    expense=Expense.objects.filter(
        date__range=(start_date,end_date)
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0



    receivable=Receivable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    payable=Payable.objects.aggregate(
        total=Sum('amount_paid')
    )['total'] or 0



    return {

        "income":income,

        "expense":expense,

        "receivable":receivable,

        "payable":payable,

        "profit":
        (income+receivable)-(expense+payable)

    }