from django import forms

from .models import (
    Order,
    Quotation,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    StockReservation,
    ProductionOutput,
    BillOfMaterial
)

from Employee.models import Employee
from inventory.models import Product, RawMaterial, Asset



# ======================================================
# CUSTOMER ORDER FORM (MANAGER)
# ======================================================

class OrderForm(forms.ModelForm):

    class Meta:

        model = Order

        fields = [
            'product',
            'customer_name',
            'customer_phone',
            'quantity_to_produce',
        ]


        widgets = {

            'product': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'customer_name': forms.TextInput(
                attrs={
                    'class':'form-control',
                    'placeholder':'Customer name'
                }
            ),


            'customer_phone': forms.TextInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'quantity_to_produce': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# ASSIGN WORKER FORM (MANAGER)
# ======================================================

class AssignWorkerForm(forms.ModelForm):


    class Meta:

        model = Order


        fields = [
            'assigned_to'
        ]


        widgets = {

            'assigned_to': forms.Select(
                attrs={
                    'class':'form-control'
                }
            )

        }




# ======================================================
# QUOTATION FORM (WORKER)
# ======================================================

class QuotationForm(forms.ModelForm):


    class Meta:

        model = Quotation


        fields = [

            'material_cost',
            'labour_cost',
            'machine_cost',
            'profit',
            'selling_price',

        ]


        widgets = {


            'material_cost': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'labour_cost': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'machine_cost': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'profit': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'selling_price': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# QUOTATION APPROVAL FORM (MANAGER)
# ======================================================

class QuotationApprovalForm(forms.ModelForm):


    class Meta:

        model = Quotation


        fields = [
            'status'
        ]


        widgets = {


            'status': forms.Select(
                attrs={
                    'class':'form-control'
                }
            )

        }




# ======================================================
# BOM FORM
# ======================================================

class BillOfMaterialForm(forms.ModelForm):


    class Meta:

        model = BillOfMaterial


        fields = [

            'product',
            'raw_material',
            'quantity_required'

        ]


        widgets = {

            'product': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'raw_material': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'quantity_required': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# MATERIAL CONSUMPTION FORM
# ======================================================

class ProductionMaterialForm(forms.ModelForm):


    class Meta:

        model = ProductionMaterial


        fields = [

            'raw_material',
            'quantity_used',
            'unit_cost'

        ]


        widgets = {


            'raw_material': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'quantity_used': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'unit_cost': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# LABOUR FORM
# ======================================================

class ProductionLabourForm(forms.ModelForm):


    class Meta:

        model = ProductionLabour


        fields = [

            'employee',
            'hours_worked',
            'hourly_rate'

        ]


        widgets = {


            'employee': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'hours_worked': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'hourly_rate': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# MACHINE USAGE FORM
# ======================================================

class ProductionMachineForm(forms.ModelForm):


    class Meta:

        model = ProductionMachine


        fields = [

            'asset',
            'hours_used',
            'hourly_cost'

        ]


        widgets = {


            'asset': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'hours_used': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),


            'hourly_cost': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# STOCK RESERVATION FORM
# ======================================================

class StockReservationForm(forms.ModelForm):


    class Meta:

        model = StockReservation


        fields = [

            'raw_material',
            'quantity'

        ]


        widgets = {


            'raw_material': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'quantity': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }




# ======================================================
# PRODUCTION OUTPUT FORM
# ======================================================

class ProductionOutputForm(forms.ModelForm):


    class Meta:

        model = ProductionOutput


        fields = [

            'product',
            'quantity_produced'

        ]


        widgets = {


            'product': forms.Select(
                attrs={
                    'class':'form-control'
                }
            ),


            'quantity_produced': forms.NumberInput(
                attrs={
                    'class':'form-control'
                }
            ),

        }