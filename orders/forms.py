from django import forms

from .models import Order, OrderItem


class OrderForm(forms.ModelForm):
    """
    Dynamic order-header form used by all WPG business units.

    Business unit and order type are selected before this form opens.
    """

    class Meta:
        model = Order

        fields = [
            "customer_name",
            "customer_phone",
            "customer_email",
            "province",
            "district",
            "sector",
            "cell",
            "village",
            "delivery_address",
            "notes",
            "discount",
            "tax",
            "expected_delivery_date",
        ]

        widgets = {
            "customer_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer full name",
                }
            ),
            "customer_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer phone number",
                }
            ),
            "customer_email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Customer email",
                }
            ),
            "province": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Province",
                }
            ),
            "district": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "District",
                }
            ),
            "sector": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Sector",
                }
            ),
            "cell": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Cell",
                }
            ),
            "village": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Village",
                }
            ),
            "delivery_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Delivery address, project site "
                        "or service location"
                    ),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Additional instructions or "
                        "general order requirements"
                    ),
                }
            ),
            "discount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "tax": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "expected_delivery_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
        }

    def __init__(
        self,
        *args,
        order_type=None,
        business_unit=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.order_type = (
            order_type
            or getattr(self.instance, "order_type", None)
        )

        self.business_unit = (
            business_unit
            or getattr(self.instance, "business_unit", None)
        )

        for field in self.fields.values():
            field.required = False

        if not self.is_bound:
            self.fields["discount"].initial = 0
            self.fields["tax"].initial = 0

        self.fields["expected_delivery_date"].input_formats = [
            "%Y-%m-%d",
        ]

        customer_fields = [
            "customer_name",
            "customer_phone",
            "customer_email",
        ]

        delivery_fields = [
            "province",
            "district",
            "sector",
            "cell",
            "village",
            "delivery_address",
            "expected_delivery_date",
        ]

        # Online customer order
        if self.order_type == "ECOMMERCE":
            self._set_required(
                "customer_name",
                "customer_phone",
                "delivery_address",
            )

        # Customer-specific furniture
        elif self.order_type == "CUSTOM_FURNITURE":
            self._set_required(
                "customer_name",
                "customer_phone",
                "delivery_address",
                "expected_delivery_date",
            )

            self.fields["notes"].label = (
                "General Customer Requirements"
            )

        # General custom request:
        # agriculture supply or construction work
        elif self.order_type == "CUSTOM_ORDER":
            self._set_required(
                "customer_name",
                "customer_phone",
                "delivery_address",
                "expected_delivery_date",
            )

            self.fields["delivery_address"].label = (
                "Delivery / Service Location"
            )

        # Construction project or contract
        elif self.order_type == "PROJECT":
            self._set_required(
                "customer_name",
                "customer_phone",
                "delivery_address",
                "expected_delivery_date",
                "notes",
            )

            self.fields["delivery_address"].label = (
                "Project Site"
            )
            self.fields["notes"].label = (
                "Project Summary"
            )

        # Maintenance and renovation work
        elif self.order_type == "MAINTENANCE":
            self._set_required(
                "customer_name",
                "customer_phone",
                "delivery_address",
                "expected_delivery_date",
                "notes",
            )

            self.fields["delivery_address"].label = (
                "Work Location"
            )
            self.fields["notes"].label = (
                "Maintenance / Renovation Description"
            )

        # Internal stock replenishment
        elif self.order_type == "RESTOCK":
            self._remove_fields(
                customer_fields + delivery_fields
            )

            self.fields["notes"].label = (
                "Restock Instructions"
            )

        # Internal prototype or product development
        elif self.order_type == "NEW_PRODUCT":
            self._remove_fields(
                customer_fields + delivery_fields
            )

            self.fields["notes"].required = True
            self.fields["notes"].label = (
                "Product Development Notes"
            )

        # Direct shop or showroom sale
        elif self.order_type == "POS":
            self._remove_fields(delivery_fields)

            self.fields["customer_name"].label = (
                "Customer Name (Optional)"
            )
            self.fields["customer_phone"].label = (
                "Customer Phone (Optional)"
            )

    def _set_required(self, *field_names):
        for field_name in field_names:
            if field_name in self.fields:
                self.fields[field_name].required = True

    def _remove_fields(self, field_names):
        for field_name in field_names:
            self.fields.pop(field_name, None)

    def _require(
        self,
        cleaned_data,
        field_name,
        message,
    ):
        if (
            field_name in self.fields
            and not cleaned_data.get(field_name)
        ):
            self.add_error(
                field_name,
                message,
            )

    def clean_discount(self):
        discount = self.cleaned_data.get("discount")

        if discount is None:
            return 0

        if discount < 0:
            raise forms.ValidationError(
                "Discount cannot be negative."
            )

        return discount

    def clean_tax(self):
        tax = self.cleaned_data.get("tax")

        if tax is None:
            return 0

        if tax < 0:
            raise forms.ValidationError(
                "Tax cannot be negative."
            )

        return tax

    def clean(self):
        cleaned_data = super().clean()

        customer_delivery_types = {
            "ECOMMERCE",
            "CUSTOM_FURNITURE",
            "CUSTOM_ORDER",
            "PROJECT",
            "MAINTENANCE",
        }

        if self.order_type in customer_delivery_types:
            self._require(
                cleaned_data,
                "customer_name",
                "Customer name is required.",
            )
            self._require(
                cleaned_data,
                "customer_phone",
                "Customer phone is required.",
            )
            self._require(
                cleaned_data,
                "delivery_address",
                (
                    "Delivery address, project site "
                    "or service location is required."
                ),
            )

        if self.order_type in {
            "CUSTOM_FURNITURE",
            "CUSTOM_ORDER",
            "PROJECT",
            "MAINTENANCE",
        }:
            self._require(
                cleaned_data,
                "expected_delivery_date",
                "Expected completion or delivery date is required.",
            )

        if self.order_type in {
            "PROJECT",
            "MAINTENANCE",
            "NEW_PRODUCT",
        }:
            self._require(
                cleaned_data,
                "notes",
                "A description is required.",
            )

        return cleaned_data


class OrderItemForm(forms.ModelForm):
    """
    Dynamic order-item form.

    Existing products:
    - ECOMMERCE
    - POS
    - RESTOCK

    Custom or service requests:
    - CUSTOM_FURNITURE
    - CUSTOM_ORDER
    - PROJECT
    - MAINTENANCE
    - NEW_PRODUCT
    """

    class Meta:
        model = OrderItem

        fields = [
            "product",
            "product_name",
            "quantity",
            "price",
            "specifications",
            "reference_image",
            "design_attachment",
            "length_cm",
            "width_cm",
            "height_cm",
            "material_preference",
            "colour",
            "finish",
            "customer_budget",
        ]

        widgets = {
            "product": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "product_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Product, service or requested item name"
                    ),
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "step": 1,
                }
            ),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "reference_image": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "design_attachment": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/*,.pdf,.doc,.docx,.xls,.xlsx"}),
            "length_cm": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "width_cm": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "height_cm": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "material_preference": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Muvula, MDF, steel, fabric"}),
            "colour": forms.TextInput(attrs={"class": "form-control", "placeholder": "Preferred colour"}),
            "finish": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. matte, gloss, natural"}),
            "customer_budget": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01"}),
            "specifications": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Dimensions, design, materials, colour, "
                        "service scope, construction requirements "
                        "or other special specifications"
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        order_type=None,
        business_unit=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.order_type = order_type
        self.business_unit = business_unit

        self.fields["product"].required = False
        self.fields["product_name"].required = False
        self.fields["specifications"].required = False
        self.fields["price"].required = False

        optional_detail_fields = [
            "reference_image", "design_attachment", "length_cm", "width_cm",
            "height_cm", "material_preference", "colour", "finish",
            "customer_budget",
        ]
        for field_name in optional_detail_fields:
            self.fields[field_name].required = False

        self.fields["product"].empty_label = (
            "Select an existing product or service"
        )

        # Get the real Product model used by OrderItem.product.
        ProductModel = (
            OrderItem
            ._meta
            .get_field("product")
            .remote_field
            .model
        )

        products = ProductModel.objects.all()

        product_field_names = {
            field.name
            for field in ProductModel._meta.fields
        }

        if (
            self.business_unit
            and "business_unit" in product_field_names
        ):
            # Marketplace may show published products
            # belonging to all business units.
            if self.business_unit != "MARKETPLACE":
                products = products.filter(
                    business_unit=self.business_unit
                )

        if "is_published" in product_field_names:
            products = products.filter(
                is_published=True
            )

        self.fields["product"].queryset = (
            products.order_by("name")
        )

        existing_product_types = {
            "ECOMMERCE",
            "POS",
            "RESTOCK",
        }

        custom_request_types = {
            "CUSTOM_FURNITURE",
            "CUSTOM_ORDER",
            "PROJECT",
            "MAINTENANCE",
            "NEW_PRODUCT",
        }

        if self.order_type in existing_product_types:
            self.fields["product"].required = True

            # Name is copied automatically from Product.
            self.fields.pop(
                "product_name",
                None,
            )

            if self.order_type != "RESTOCK":
                self.fields["specifications"].required = False

            if self.order_type in {"ECOMMERCE", "POS"}:
                self.fields.pop("price", None)
                for field_name in optional_detail_fields:
                    self.fields.pop(field_name, None)

            elif self.order_type == "RESTOCK":
                self.fields.pop("price", None)
                for field_name in [
                    "design_attachment", "length_cm", "width_cm", "height_cm",
                    "material_preference", "colour", "finish", "customer_budget",
                ]:
                    self.fields.pop(field_name, None)

        elif self.order_type in custom_request_types:
            self.fields["product_name"].required = True
            self.fields["specifications"].required = True

            self.fields["product"].label = (
                "Related Existing Product / Service (Optional)"
            )

            if self.order_type == "PROJECT":
                self.fields["product_name"].label = (
                    "Project / Contract Name"
                )
                self.fields["specifications"].label = (
                    "Project Scope and Requirements"
                )

            elif self.order_type == "MAINTENANCE":
                self.fields["product_name"].label = (
                    "Maintenance / Renovation Service"
                )
                self.fields["specifications"].label = (
                    "Work Description"
                )

            elif self.order_type == "NEW_PRODUCT":
                self.fields["product_name"].label = (
                    "Proposed Product Name"
                )
                self.fields["specifications"].label = (
                    "Product Development Specifications"
                )
                self.fields.pop("price", None)
                self.fields.pop("customer_budget", None)
                self.fields["design_attachment"].required = True
                self.fields["design_attachment"].label = "Design / Reference Attachment"

            elif self.order_type == "CUSTOM_FURNITURE":
                self.fields["product_name"].label = (
                    "Furniture Requested"
                )
                self.fields["specifications"].label = (
                    "Furniture Specifications"
                )
                self.fields["price"].label = "Quoted Unit Price"
                self.fields["reference_image"].label = "Reference Photo"
                self.fields["customer_budget"].label = "Customer Budget (Optional)"

    def clean_quantity(self):
        quantity = self.cleaned_data.get(
            "quantity"
        )

        if quantity is None or quantity < 1:
            raise forms.ValidationError(
                "Quantity must be at least one."
            )

        return quantity

    def clean(self):
        cleaned_data = super().clean()

        product = cleaned_data.get("product")

        product_name = (
            cleaned_data.get("product_name")
            or ""
        ).strip()

        specifications = (
            cleaned_data.get("specifications")
            or ""
        ).strip()

        existing_product_types = {
            "ECOMMERCE",
            "POS",
            "RESTOCK",
        }

        custom_request_types = {
            "CUSTOM_FURNITURE",
            "CUSTOM_ORDER",
            "PROJECT",
            "MAINTENANCE",
            "NEW_PRODUCT",
        }

        if (
            self.order_type in existing_product_types
            and not product
        ):
            self.add_error(
                "product",
                "Select an existing product.",
            )

        if self.order_type in custom_request_types:
            if not product_name:
                self.add_error(
                    "product_name",
                    (
                        "Enter the requested product, "
                        "service or project name."
                    ),
                )

            if not specifications:
                self.add_error(
                    "specifications",
                    (
                        "Enter the specifications or "
                        "scope of work."
                    ),
                )

        return cleaned_data
