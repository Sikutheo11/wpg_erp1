from django import forms
from .models import (Product, RawMaterial, Asset, StockMovement, AssetAssignment)



# ==================================================
# COMMON BOOTSTRAP STYLE
# ==================================================

class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs.update({"class":"form-select"})
            elif isinstance(widget, forms.Textarea):
                widget.attrs.update({
                    "class":"form-control",
                    "rows":4
                })

            else:
                widget.attrs.update({
                    "class":
                    "form-control"
                })



# ==================================================
# RAW MATERIAL FORM
# ==================================================

class RawMaterialForm(BootstrapFormMixin,forms.ModelForm):

    class Meta:
        model = RawMaterial

        fields = [
            'supplier',
            'name',
            'code',
            'status',
            'unit',
            'minimum_stock',
            'unit_cost',
        ]


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()



# ==================================================
# PRODUCT FORM
# ==================================================

class ProductForm( BootstrapFormMixin,forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            'category',
            'product_code',
            'name',
            'description',
            'unit',
            'selling_price',
            'reorder_level',
        ]


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()



# ==================================================
# ASSET FORM
# ==================================================

class AssetForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Asset
        fields = [
            'asset_type',
            'name',
            'purchase_cost',
            'purchase_date',
            'status',
        ]
        widgets = {
            "purchase_date":
            forms.DateInput(
                attrs={"type": "date"}
            )

        }


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()



# ==================================================
# ASSET ASSIGNMENT FORM
# ==================================================

class AssetAssignmentForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = AssetAssignment
        fields = [
            'asset',
            'department',
            'employee',
            'assigned_date',
            'returned_date',
        ]


        widgets = {
            "assigned_date":
            forms.DateInput(
                attrs={
                    "type":"date"
                }
            ),


            "returned_date":
            forms.DateInput(
                attrs={
                    "type":"date"
                }
            )

        }


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()



# ==================================================
# STOCK MOVEMENT FORM
# ==================================================

class StockMovementForm(
    BootstrapFormMixin,
    forms.ModelForm
):

    class Meta:

        model = StockMovement

        fields = [

            'product',
            'raw_material',
            'movement_type',
            'quantity',
            'unit_cost',
            'reference_no',

        ]


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()



    # validation
    def clean(self):

        cleaned_data = super().clean()


        product = cleaned_data.get(
            "product"
        )

        material = cleaned_data.get(
            "raw_material"
        )


        if not product and not material:

            raise forms.ValidationError(
                "Select Product or Raw Material"
            )


        if product and material:

            raise forms.ValidationError(
                "Choose only Product OR Raw Material"
            )


        return cleaned_data