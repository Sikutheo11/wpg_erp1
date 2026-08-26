from django import forms
from .models import (
    Asset,
    AssetAssignment,
    Category,
    Product,
    RawMaterial,
    StockMovement,
    Supplier,
    Warehouse,
)



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


class CategoryForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class WarehouseForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "name",
            "code",
            "warehouse_type",
            "business_unit",
            "location",
            "manager",
            "is_active",
            "allow_negative_stock",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class SupplierForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "tax_number",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()



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

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get("department")
        employee = cleaned_data.get("employee")
        assigned_date = cleaned_data.get("assigned_date")
        returned_date = cleaned_data.get("returned_date")

        if employee and employee.department_id != getattr(department, "pk", None):
            self.add_error(
                "employee",
                "The selected employee must belong to the selected department.",
            )

        if assigned_date and returned_date and returned_date < assigned_date:
            self.add_error(
                "returned_date",
                "Returned date cannot be earlier than assigned date.",
            )

        return cleaned_data



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
