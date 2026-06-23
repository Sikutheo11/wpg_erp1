from django import forms
from django.forms import inlineformset_factory

from .models import (
    Customer,
    SalesQuotation,
    SalesQuotationItem,
    Sale,
    SaleItem,
    Invoice,
    CustomerPayment,
)


# ==========================================
# CUSTOMER FORM
# ==========================================

class CustomerForm(forms.ModelForm):

    class Meta:

        model = Customer

        fields = [
            'user',
            'company_name',
            'phone',
            'address',
        ]

        widgets = {

            'user': forms.Select(
                attrs={
                    'class': 'form-select'
                }
            ),

            'company_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Company name'
                }
            ),

            'phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Phone number'
                }
            ),

            'address': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Address'
                }
            ),
        }



# ==========================================
# SALES QUOTATION FORM
# ==========================================

class SalesQuotationForm(forms.ModelForm):

    class Meta:

        model = SalesQuotation

        fields = [
            'customer',
            'quotation_no',
            'quotation_date',
            'valid_until',
            'discount',
            'tax',
            'status',
            'notes',
        ]


        widgets = {

            'customer': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'quotation_no': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'quotation_date': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'valid_until': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'discount': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'tax': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'status': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'notes': forms.Textarea(
                attrs={
                    'class':'form-control',
                    'rows':3
                }
            ),
        }



# ==========================================
# QUOTATION ITEM FORM
# ==========================================

class SalesQuotationItemForm(forms.ModelForm):

    class Meta:

        model = SalesQuotationItem

        fields = [
            'product',
            'quantity',
            'unit_price',
        ]


        widgets = {

            'product': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'quantity': forms.NumberInput(
                attrs={
                    'class':'form-control',
                    'step':'0.01'
                }
            ),


            'unit_price': forms.NumberInput(
                attrs={
                    'class':'form-control',
                    'step':'0.01'
                }
            ),

        }



# ==========================================
# SALE FORM
# ==========================================

class SaleForm(forms.ModelForm):

    class Meta:

        model = Sale


        fields = [
            'customer',
            'quotation',
            'sale_no',
            'sale_date',
            'discount',
            'tax',
            'status',
        ]


        widgets = {


            'customer': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'quotation': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'sale_no': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'sale_date': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'discount': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'tax': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'status': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),

        }



# ==========================================
# SALE ITEM FORM
# ==========================================

class SaleItemForm(forms.ModelForm):

    class Meta:

        model = SaleItem

        fields = [
            'product',
            'quantity',
            'unit_price',
        ]


        widgets = {


            'product': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'quantity': forms.NumberInput(
                attrs={
                    'class':'form-control',
                    'step':'0.01'
                }
            ),


            'unit_price': forms.NumberInput(
                attrs={
                    'class':'form-control',
                    'step':'0.01'
                }
            ),
        }


# ==========================================
# SALE ITEM INLINE FORMSET
# ==========================================

SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    extra=1,
    can_delete=True
)



# ==========================================
# INVOICE FORM
# ==========================================

class InvoiceForm(forms.ModelForm):

    class Meta:

        model = Invoice


        fields = [
            'sale',
            'invoice_no',
            'invoice_date',
            'due_date',
            'total_amount',
            'amount_paid',
            'status',
        ]


        widgets = {


            'sale': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'invoice_no': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'invoice_date': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'due_date': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'total_amount': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'amount_paid': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'status': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),
        }



# ==========================================
# CUSTOMER PAYMENT FORM
# ==========================================

class CustomerPaymentForm(forms.ModelForm):

    class Meta:

        model = CustomerPayment


        fields = [
            'invoice',
            'amount',
            'payment_method',
            'payment_date',
            'reference',
            'notes',
        ]


        widgets = {


            'invoice': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'amount': forms.NumberInput(
                attrs={
                    'class':'form-control',
                    'step':'0.01'
                }
            ),


            'payment_method': forms.Select(
                attrs={
                    'class':'form-select'
                }
            ),


            'payment_date': forms.DateInput(
                attrs={
                    'class':'form-control',
                    'type':'date'
                }
            ),


            'reference': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'notes': forms.Textarea(
                attrs={
                    'class':'form-control',
                    'rows':3
                }
            ),
        }