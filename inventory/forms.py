from django import forms
from core.file_validators import validate_image_upload
from Employee.models import Employee
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
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({"class": "form-check-input"})
            elif isinstance(widget, forms.Select):
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
        self.fields["code"].required = False
        self.fields["code"].help_text = (
            "Leave blank to generate a code from the warehouse name."
        )
        self.fields["manager"].queryset = Employee.objects.filter(
            is_active=True
        ).select_related("user").order_by("user__first_name", "user__last_name")
        self.fields["manager"].required = False
        self.fields["allow_negative_stock"].help_text = (
            "Keep disabled unless Finance and Inventory management explicitly approve it."
        )


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
        self.fields["contact_person"].help_text = (
            "Optional person WPG should contact about purchases or deliveries."
        )
        self.fields["tax_number"].label = "Tax identification number (TIN)"
        self.fields["tax_number"].help_text = "Optional; use the supplier's registered TIN."



# ==================================================
# RAW MATERIAL FORM
# ==================================================

class RawMaterialForm(BootstrapFormMixin,forms.ModelForm):

    class Meta:
        model = RawMaterial

        fields = [
            'supplier',
            'category',
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
        self.fields['supplier'].required = False
        self.fields['supplier'].help_text = (
            'Optional preferred supplier for this material.'
        )
        self.fields['minimum_stock'].help_text = (
            'The system raises a low-stock alert at or below this quantity.'
        )
        self.fields['unit_cost'].help_text = (
            'Current estimated cost per selected unit.'
        )



# ==================================================
# PRODUCT FORM
# ==================================================

class ProductForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            'business_unit',
            'product_type',
            'category',
            'preferred_supplier',
            'product_code',
            'name',
            'description',
            'unit',
            'standard_cost',
            'selling_price',
            'reorder_level',
            'reorder_quantity',
            'valuation_method',
            'track_inventory',
            'allow_negative_stock',
            'is_active',
            'is_published',
            'is_featured',
            'image',
        ]


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()
        self.fields['product_code'].required = False
        self.fields['product_code'].help_text = (
            'Leave blank to generate the code automatically.'
        )
        self.fields['standard_cost'].help_text = (
            'Approved production or purchase cost used for valuation.'
        )
        self.fields['selling_price'].help_text = (
            'Customer price. Publishing requires a positive selling price.'
        )
        self.fields['is_published'].help_text = (
            'Makes this product eligible for the Marketplace catalogue.'
        )
        self.fields['image'].help_text = (
            'Optional JPG, PNG or WebP image, maximum 5 MB.'
        )

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'content_type'):
            validate_image_upload(image)
        return image

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('is_published'):
            if not cleaned.get('is_active'):
                self.add_error(
                    'is_active',
                    'A published product must be active.',
                )
            if (cleaned.get('selling_price') or 0) <= 0:
                self.add_error(
                    'selling_price',
                    'Enter a selling price before publishing.',
                )
        if cleaned.get('product_type') == 'SERVICE':
            cleaned['track_inventory'] = False
            cleaned['reorder_level'] = 0
            cleaned['reorder_quantity'] = 0
        return cleaned



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
        current_asset_id = getattr(self.instance, "asset_id", None)
        unavailable_asset_ids = AssetAssignment.objects.filter(
            returned_date__isnull=True,
        ).exclude(pk=self.instance.pk).values_list("asset_id", flat=True)
        self.fields["asset"].queryset = Asset.objects.filter(
            status="active",
        ).exclude(pk__in=unavailable_asset_ids).order_by("name")
        if current_asset_id:
            self.fields["asset"].queryset = Asset.objects.filter(
                pk=current_asset_id,
            ) | self.fields["asset"].queryset

        department_id = None
        if self.is_bound:
            department_id = self.data.get(self.add_prefix("department"))
        elif self.instance.pk:
            department_id = self.instance.department_id
        self.fields["employee"].queryset = Employee.objects.filter(
            is_active=True,
        ).select_related("user", "department").order_by(
            "user__first_name", "user__last_name"
        )
        if department_id:
            self.fields["employee"].queryset = self.fields[
                "employee"
            ].queryset.filter(department_id=department_id)
        self.fields["employee"].required = False
        self.fields["employee"].help_text = (
            "Optional. Leave blank when the department keeps custody of the asset."
        )
        self.fields["returned_date"].required = False
        self.fields["returned_date"].help_text = (
            "Leave blank while the assignment is active."
        )

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
            'warehouse',
            'movement_type',
            'quantity',
            'unit_cost',
            'reference_type',
            'reference_no',
            'notes',
        ]


    def __init__(self,*args,**kwargs):

        super().__init__(
            *args,
            **kwargs
        )

        self.apply_bootstrap()
        self.fields["product"].queryset = Product.objects.filter(
            is_active=True,
            track_inventory=True,
        ).order_by("business_unit", "name")
        self.fields["warehouse"].queryset = Warehouse.objects.filter(
            is_active=True,
        ).order_by("warehouse_type", "name")
        self.fields["movement_type"].choices = [
            choice
            for choice in StockMovement.MOVEMENT_TYPES
            if choice[0] not in {"TRANSFER_IN", "TRANSFER_OUT"}
        ]
        self.fields["unit_cost"].required = False
        self.fields["unit_cost"].help_text = (
            "Optional. Leave blank to use the product's standard cost."
        )
        self.fields["reference_no"].help_text = (
            "Optional purchase, order, job, count or return reference."
        )
        self.fields["notes"].help_text = (
            "Explain manual adjustments and unusual stock changes."
        )



    # validation
    def clean(self):

        cleaned_data = super().clean()


        product = cleaned_data.get(
            "product"
        )

        quantity = cleaned_data.get("quantity")
        movement_type = cleaned_data.get("movement_type")
        if not product:
            self.add_error("product", "Select an active inventory product.")
        if quantity is not None and quantity <= 0:
            self.add_error("quantity", "Quantity must be greater than zero.")
        if product and cleaned_data.get("unit_cost") is None:
            cleaned_data["unit_cost"] = product.standard_cost
        if movement_type in {"ADJUSTMENT_IN", "ADJUSTMENT_OUT"} and not (
            cleaned_data.get("notes") or ""
        ).strip():
            self.add_error("notes", "Explain why this stock adjustment is required.")


        return cleaned_data
