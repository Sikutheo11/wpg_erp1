from django import forms
from django.db.models import Q
from inventory.models import Product
from .models import (
    EcommercePayment,
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerProductAssignment,
)
from .services.payment_provider_service import (
    PaymentProviderConfigurationService,
)

class BootstrapFormMixin:
    def _apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(
                widget,
                (
                    forms.Select,
                    forms.SelectMultiple,
                ),
            ):
                css_class = "form-select"
            else:
                css_class = "form-control"

            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{existing} {css_class}".strip()


class OnlineProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OnlineProduct
        fields = [
            "product",
            "title",
            "slug",
            "image",
            "short_description",
            "description",
            "purchase_mode",
            "minimum_order_quantity",
            "maximum_order_quantity",
            "seo_title",
            "seo_description",
        ]
        widgets = {
            "short_description": forms.Textarea(
                attrs={"rows": 2}
            ),
            "description": forms.Textarea(
                attrs={"rows": 5}
            ),
            "seo_description": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        product_queryset = (
            Product.objects
            .filter(
                is_active=True,
                business_unit__in={
                    "FURNITURE",
                    "CONSTRUCTION",
                    "AGRICULTURE",
                },
            )
            .filter(online_product__isnull=True)
            .select_related("category")
            .order_by("business_unit", "name")
        )

        if self.instance and self.instance.pk:
            product_queryset = (
                Product.objects
                .filter(
                    Q(online_product__isnull=True)
                    | Q(pk=self.instance.product_id),
                    business_unit__in={
                        "FURNITURE",
                        "CONSTRUCTION",
                        "AGRICULTURE",
                    },
                )
                .select_related("category")
                .order_by("business_unit", "name")
                .distinct()
            )

        self.fields["product"].queryset = product_queryset
        self.fields["product"].help_text = (
            "Price, stock, publication and business unit are managed "
            "by the shared Inventory Product."
        )
        self.fields["slug"].required = False
        self._apply_bootstrap()

    def clean_slug(self):
        return (self.cleaned_data.get("slug") or "").strip().lower()


class CheckoutForm(BootstrapFormMixin, forms.Form):
    full_name = forms.CharField(
        max_length=200,
        label="Full name",
    )
    phone = forms.CharField(
        max_length=30,
        label="Phone number",
    )
    email = forms.EmailField(
        required=False,
        label="Email address",
    )
    province = forms.CharField(max_length=100)
    district = forms.CharField(max_length=100)
    sector = forms.CharField(max_length=100)
    cell = forms.CharField(
        max_length=100,
        required=False,
    )
    village = forms.CharField(
        max_length=100,
        required=False,
    )
    delivery_address = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Additional notes",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self._apply_bootstrap()

        self.fields["full_name"].widget.attrs.update(
            {"placeholder": "Customer full name"}
        )
        self.fields["phone"].widget.attrs.update(
            {"placeholder": "e.g. 0788000000"}
        )
        self.fields["email"].widget.attrs.update(
            {"placeholder": "customer@example.com"}
        )
        self.fields["delivery_address"].widget.attrs.update(
            {"placeholder": "Delivery location and directions"}
        )

    def clean_phone(self):
        phone = "".join(
            character
            for character in self.cleaned_data["phone"].strip()
            if character not in {" ", "-", "(", ")"}
        )

        if phone.startswith("+"):
            digits = phone[1:]
        else:
            digits = phone

        if not digits.isdigit() or len(digits) < 9:
            raise forms.ValidationError(
                "Enter a valid phone number."
            )

        return phone

    def clean(self):
        cleaned_data = super().clean()

        required_location_fields = (
            "province",
            "district",
            "sector",
            "delivery_address",
        )

        for field_name in required_location_fields:
            value = cleaned_data.get(field_name)
            if isinstance(value, str):
                cleaned_data[field_name] = value.strip()

        return cleaned_data

class EcommercePaymentForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    """Customer-facing payment-provider form."""

    PROVIDER_METHODS = {
        "MTN_MOMO": EcommercePayment.MOBILE_MONEY,
        "AIRTEL_MONEY": EcommercePayment.MOBILE_MONEY,
        "RSWITCH_CARD": EcommercePayment.CARD,
        "EKASH": EcommercePayment.EKASH,
    }

    provider = forms.ChoiceField(
        choices=(),
        label="Payment channel",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    class Meta:
        model = EcommercePayment
        fields = [
            "method",
            "provider",
            "customer_reference",
        ]
        widgets = {
            "method": forms.HiddenInput(),
            "customer_reference": forms.TextInput(
                attrs={
                    "placeholder": (
                        "Enter the phone number that will pay"
                    ),
                    "autocomplete": "tel",
                }
            ),
        }
        labels = {
            "customer_reference": "Payment phone number",
       }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = (
            PaymentProviderConfigurationService
            .customer_provider_choices()
        )

        self.fields["provider"].choices = choices
        self.fields["method"].required = False
        self.fields["customer_reference"].required = True
        self.has_available_providers = bool(choices)

        self._apply_bootstrap()

        if not self.is_bound and choices:
            default_provider = choices[0][0]

            self.initial.setdefault(
                "provider",
                default_provider,
            )
            self.initial.setdefault(
                "method",
                self.PROVIDER_METHODS[
                    default_provider
                ],
            )

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get("provider")

        if not provider:
            if not self.has_available_providers:
                raise forms.ValidationError(
                    (
                        "No payment channel is currently "
                        "available. Please try again later."
                    )
                )
            return cleaned_data

        if not (
            PaymentProviderConfigurationService
            .customer_provider_is_available(provider)
        ):
            self.add_error(
                "provider",
                (
                    "This payment channel is not currently "
                    "available."
                ),
            )
            return cleaned_data

        method = self.PROVIDER_METHODS.get(provider)

        if not method:
            self.add_error(
                "provider",
                "Unsupported payment channel.",
            )
            return cleaned_data

        cleaned_data["method"] = method

        phone = "".join(
            character
            for character in str(
                cleaned_data.get(
                    "customer_reference",
                    "",
                )
            )
            if character.isdigit()
        )

        if (
            len(phone) == 12
            and phone.startswith("250")
        ):
            phone = f"0{phone[3:]}"

        if (
            len(phone) != 10
            or not phone.startswith("07")
        ):
            self.add_error(
                "customer_reference",
                (
                    "Enter a valid Rwanda phone number, "
                    "for example 0788000000."
                ),
            )
        else:
            cleaned_data["customer_reference"] = phone

        return cleaned_data


class PaymentConfirmationForm(forms.Form):
    provider_reference = forms.CharField(
        max_length=120,
        label="Confirmed provider reference",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Verified MoMo or bank reference",
                "autocomplete": "off",
            }
        ),
    )

    def clean_provider_reference(self):
        reference = self.cleaned_data["provider_reference"].strip()
        if len(reference) < 3:
            raise forms.ValidationError(
                "Enter a valid provider payment reference."
            )
        return reference

class PaymentRefundForm(BootstrapFormMixin, forms.Form):
    reason = forms.CharField(
        label="Refund reason",
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": (
                    "Explain why this customer payment "
                    "must be refunded."
                ),
            }
        ),
    )

    confirm_refund = forms.BooleanField(
        required=True,
        label=(
            "I confirm that the full customer payment "
            "should be refunded."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()

        if len(reason) < 5:
            raise forms.ValidationError(
                "Provide a clear refund reason."
            )

        return reason

class MarketplaceSellerForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = MarketplaceSeller
        fields = [
            "name",
            "seller_type",
            "poultry_farm",
            "contact_name",
            "phone",
            "email",
            "default_commission_rate",
            "payable_account",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "Seller or farm business name"}
            ),
            "contact_name": forms.TextInput(
                attrs={"placeholder": "Contact person"}
            ),
            "phone": forms.TextInput(
                attrs={"placeholder": "e.g. 0788000000"}
            ),
            "default_commission_rate": forms.NumberInput(
                attrs={
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["poultry_farm"].queryset = (
            self.fields["poultry_farm"]
            .queryset
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["payable_account"].queryset = (
            self.fields["payable_account"]
            .queryset
            .filter(
                account_type="LIABILITY",
                is_active=True,
            )
            .order_by("code")
        )

        self.fields["payable_account"].initial = (
            self.fields["payable_account"]
            .queryset
            .filter(code="2200")
            .first()
        )

        self.fields["default_commission_rate"].help_text = (
            "WPG-owned sellers use 0%. Independent sellers must have "
            "the commission percentage agreed with WPG."
        )

        self._apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        seller_type = cleaned_data.get("seller_type")
        commission_rate = cleaned_data.get(
            "default_commission_rate"
        )

        if seller_type == MarketplaceSeller.WPG_INTERNAL:
            cleaned_data["default_commission_rate"] = 0

        if (
            seller_type == MarketplaceSeller.INDEPENDENT
            and (
                commission_rate is None
                or commission_rate <= 0
            )
        ):
            self.add_error(
                "default_commission_rate",
                (
                    "Enter the commission percentage agreed "
                    "with this independent seller."
                ),
            )

        return cleaned_data


class SellerProductAssignmentForm(
    BootstrapFormMixin,
    forms.ModelForm,
):
    class Meta:
        model = SellerProductAssignment
        fields = [
            "online_product",
            "seller",
            "commission_rate",
            "effective_from",
            "is_active",
        ]
        widgets = {
            "effective_from": forms.DateInput(
                attrs={"type": "date"}
            ),
            "commission_rate": forms.NumberInput(
                attrs={
                    "min": "0",
                    "max": "100",
                    "step": "0.01",
                }
            ),
        }

    def __init__(
        self,
        *args,
        online_product=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.online_product = online_product

        self.fields["seller"].queryset = (
            MarketplaceSeller.objects
            .filter(is_active=True)
            .select_related("poultry_farm")
            .order_by("name")
        )

        product_queryset = (
            OnlineProduct.objects
            .select_related("product")
            .order_by(
                "product__business_unit",
                "product__name",
            )
        )

        if online_product is not None:
            product_queryset = product_queryset.filter(
                pk=online_product.pk
            )
            self.fields["online_product"].initial = (
                online_product
            )
            self.fields["online_product"].disabled = True

        self.fields["online_product"].queryset = product_queryset
        self.fields["commission_rate"].required = False
        self.fields["commission_rate"].help_text = (
            "Leave blank to use the seller's default commission. "
            "WPG-owned products always use 0%."
        )

        self._apply_bootstrap()

    def clean(self):
        cleaned_data = super().clean()

        online_product = (
            self.online_product
            or cleaned_data.get("online_product")
        )
        seller = cleaned_data.get("seller")
        commission_rate = cleaned_data.get(
            "commission_rate"
        )

        if not online_product or not seller:
            return cleaned_data

        if (
            online_product.product.business_unit
            == "AGRICULTURE"
            and seller.poultry_farm_id is None
        ):
            self.add_error(
                "seller",
                (
                    "An Agriculture product must use a seller "
                    "linked to a poultry farm."
                ),
            )

        if seller.is_internal:
            cleaned_data["commission_rate"] = 0
        elif (
            commission_rate is not None
            and commission_rate <= 0
        ):
            self.add_error(
                "commission_rate",
                (
                    "Independent seller commission must be "
                    "greater than zero."
                ),
            )

        return cleaned_data


class SellerSettlementCreateForm(
    BootstrapFormMixin,
    forms.Form,
):
    sale_lines = forms.ModelMultipleChoiceField(
        queryset=MarketplaceOrderLine.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Eligible delivered sales",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(
        self,
        *args,
        seller,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.seller = seller
        self.fields["sale_lines"].queryset = (
            MarketplaceOrderLine.objects
            .filter(
                seller=seller,
                settlement_status=(
                    MarketplaceOrderLine.ELIGIBLE
                ),
                settlement_line__isnull=True,
            )
            .select_related(
                "order_item__order",
                "farm",
            )
            .order_by(
                "order_item__order__order_number",
                "pk",
            )
        )

        self._apply_bootstrap()

        # Checkbox widgets use Bootstrap's checkbox class.
        self.fields[
            "sale_lines"
        ].widget.attrs["class"] = "form-check-input"

    def clean_sale_lines(self):
        lines = self.cleaned_data["sale_lines"]

        if not lines.exists():
            raise forms.ValidationError(
                "Select at least one eligible sale."
            )

        invalid = lines.exclude(
            seller=self.seller,
            settlement_status=(
                MarketplaceOrderLine.ELIGIBLE
            ),
        ).exists()

        if invalid:
            raise forms.ValidationError(
                (
                    "Every selected sale must be eligible "
                    "and belong to this seller."
                )
            )

        return lines


class SellerSettlementPaymentForm(
    BootstrapFormMixin,
    forms.Form,
):
    PAYMENT_METHODS = (
        ("cash", "Cash"),
        ("bank", "Bank"),
        ("mobile_money", "Mobile Money"),
    )

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
    )
    payment_reference = forms.CharField(
        max_length=120,
        label="Payment reference",
        widget=forms.TextInput(
            attrs={
                "placeholder": (
                    "Bank, cash receipt or Mobile Money reference"
                )
            }
        ),
    )
    payment_date = forms.DateField(
        widget=forms.DateInput(
            attrs={"type": "date"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean_payment_reference(self):
        reference = self.cleaned_data[
            "payment_reference"
        ].strip()

        if len(reference) < 3:
            raise forms.ValidationError(
                "Enter a valid payment reference."
            )

        return reference