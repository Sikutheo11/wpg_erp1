from django import forms

from .models import (
    Account,
    Income,
    Expense,
    Receivable,
    Payable,
    Payment,
    Payroll
)



# =====================================================
# ACCOUNT FORM
# =====================================================

class AccountForm(forms.ModelForm):

    class Meta:

        model = Account

        fields = [
            'name',
            'account_type',
            'account_number',
            'balance'
        ]

        widgets = {

            'name': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),

            'account_type': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),

            'account_number': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),

            'balance': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }





# =====================================================
# INCOME FORM
# =====================================================

class IncomeForm(forms.ModelForm):

    class Meta:

        model = Income

        fields = [
            'account',
            'title',
            'income_type',
            'amount',
            'date',
            'sale'
        ]


        widgets = {

            'account':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),

            'title':forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'income_type':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'amount':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'date':forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'sale':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),

        }







# =====================================================
# EXPENSE FORM
# =====================================================

class ExpenseForm(forms.ModelForm):

    class Meta:

        model = Expense

        fields = [
            'account',
            'title',
            'expense_type',
            'amount',
            'date',
            'supplier'
        ]


        widgets={


            'account':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'title':forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'expense_type':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'amount':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'date':forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'supplier':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),

        }







# =====================================================
# RECEIVABLE FORM
# =====================================================

class ReceivableForm(forms.ModelForm):

    class Meta:

        model = Receivable

        fields = [

            'customer',
            'invoice_number',
            'total_amount',
            'amount_paid',
            'due_date'

        ]


        widgets={

            'customer':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'invoice_number':forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'total_amount':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'amount_paid':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'due_date':forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),

        }








# =====================================================
# PAYABLE FORM
# =====================================================

class PayableForm(forms.ModelForm):

    class Meta:

        model = Payable

        fields=[

            'supplier',
            'reference',
            'total_amount',
            'amount_paid',
            'due_date'

        ]


        widgets={

            'supplier':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'reference':forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'total_amount':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'amount_paid':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'due_date':forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),

        }









# =====================================================
# PAYMENT FORM
# =====================================================

class PaymentForm(forms.ModelForm):

    class Meta:

        model = Payment

        fields=[

            'amount',
            'method',
            'receivable',
            'payable',
            'notes'

        ]


        widgets={


            'amount':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'method':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'receivable':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'payable':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'notes':forms.Textarea(
                attrs={
                    'class':'form-control',
                    'rows':3
                }
            )

        }









# =====================================================
# PAYROLL FORM
# =====================================================

class PayrollForm(forms.ModelForm):

    class Meta:

        model = Payroll

        fields=[

            'employee',
            'month',
            'basic_salary',
            'overtime_hours',
            'overtime_rate',
            'deductions'

        ]



        widgets={


            'employee':forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'month':forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'basic_salary':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'overtime_hours':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'overtime_rate':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'deductions':forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


        }