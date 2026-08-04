from django.contrib import admin

from .models import (
    EcommerceCheckout,
    EcommerceCheckoutOrder,
    EcommercePayment,
    MarketplaceOrderLine,
    MarketplaceSeller,
    OnlineProduct,
    SellerProductAssignment,
    SellerSettlement,
    SellerSettlementLine,
)


class SellerProductAssignmentInline(admin.StackedInline):
    model = SellerProductAssignment
    fields = (
        "seller",
        "commission_rate",
        "effective_from",
        "is_active",
        "effective_rate_display",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "effective_rate_display",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("seller",)
    extra = 0
    max_num = 1
    can_delete = False

    @admin.display(description="Effective commission")
    def effective_rate_display(self, obj):
        if not obj or not obj.pk:
            return "Save the assignment to calculate the effective rate."
        return f"{obj.effective_commission_rate:,.2f}%"


@admin.register(OnlineProduct)
class OnlineProductAdmin(admin.ModelAdmin):
    list_display = (
        "display_title",
        "product",
        "business_unit_display",
        "seller_display",
        "commission_display",
        "product_type",
        "purchase_mode",
        "selling_price_display",
        "published",
        "featured",
        "views",
        "updated_at",
    )
    list_filter = (
        "purchase_mode",
        "product__business_unit",
        "product__product_type",
        "product__is_active",
        "product__is_published",
        "product__is_featured",
        "seller_assignment__seller__seller_type",
        "seller_assignment__is_active",
    )
    search_fields = (
        "title",
        "slug",
        "short_description",
        "description",
        "seo_title",
        "seo_description",
        "product__product_code",
        "product__name",
        "seller_assignment__seller__code",
        "seller_assignment__seller__name",
        "seller_assignment__seller__poultry_farm__code",
        "seller_assignment__seller__poultry_farm__name",
    )
    raw_id_fields = ("product",)
    readonly_fields = (
        "views",
        "created_at",
        "updated_at",
        "inventory_business_unit",
        "inventory_product_type",
        "inventory_selling_price",
        "inventory_publication_status",
    )
    fieldsets = (
        (
            "Inventory Product",
            {
                "fields": (
                    "product",
                    "inventory_business_unit",
                    "inventory_product_type",
                    "inventory_selling_price",
                    "inventory_publication_status",
                )
            },
        ),
        (
            "Online Presentation",
            {
                "fields": (
                    "title",
                    "slug",
                    "image",
                    "short_description",
                    "description",
                )
            },
        ),
        (
            "Selling Rules",
            {
                "fields": (
                    "purchase_mode",
                    "minimum_order_quantity",
                    "maximum_order_quantity",
                )
            },
        ),
        (
            "Search Engine Metadata",
            {
                "classes": ("collapse",),
                "fields": ("seo_title", "seo_description"),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": ("views", "created_at", "updated_at"),
            },
        ),
    )
    inlines = (SellerProductAssignmentInline,)
    ordering = ("product__business_unit", "product__name")
    list_select_related = ("product", "product__category")
    save_on_top = True

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "product",
                "product__category",
                "seller_assignment",
                "seller_assignment__seller",
                "seller_assignment__seller__poultry_farm",
            )
        )

    @admin.display(description="Online title", ordering="title")
    def display_title(self, obj):
        return obj.display_title

    @admin.display(description="Business unit", ordering="product__business_unit")
    def business_unit_display(self, obj):
        return obj.product.get_business_unit_display()

    @admin.display(description="Seller")
    def seller_display(self, obj):
        assignment = getattr(obj, "seller_assignment", None)
        return assignment.seller if assignment else "Not assigned"

    @admin.display(description="Commission")
    def commission_display(self, obj):
        assignment = getattr(obj, "seller_assignment", None)
        if not assignment:
            return "â€”"
        return f"{assignment.effective_commission_rate:,.2f}%"

    @admin.display(description="Product type", ordering="product__product_type")
    def product_type(self, obj):
        return obj.product.get_product_type_display()

    @admin.display(description="Selling price", ordering="product__selling_price")
    def selling_price_display(self, obj):
        return f"{obj.product.selling_price:,.2f} RWF"

    @admin.display(description="Published", boolean=True, ordering="product__is_published")
    def published(self, obj):
        return obj.product.is_published

    @admin.display(description="Featured", boolean=True, ordering="product__is_featured")
    def featured(self, obj):
        return obj.product.is_featured

    @admin.display(description="Inventory business unit")
    def inventory_business_unit(self, obj):
        return (
            obj.product.get_business_unit_display()
            if obj and obj.product_id
            else "Save the online product to view this value."
        )

    @admin.display(description="Inventory product type")
    def inventory_product_type(self, obj):
        return (
            obj.product.get_product_type_display()
            if obj and obj.product_id
            else "Save the online product to view this value."
        )

    @admin.display(description="Inventory selling price")
    def inventory_selling_price(self, obj):
        return (
            f"{obj.product.selling_price:,.2f} RWF"
            if obj and obj.product_id
            else "Save the online product to view this value."
        )

    @admin.display(description="Inventory publication")
    def inventory_publication_status(self, obj):
        if not obj or not obj.product_id:
            return "Save the online product to view this value."
        active = "Active" if obj.product.is_active else "Inactive"
        published = "Published" if obj.product.is_published else "Not published"
        featured = "Featured" if obj.product.is_featured else "Not featured"
        return f"{active}; {published}; {featured}"


@admin.register(MarketplaceSeller)
class MarketplaceSellerAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "seller_type",
        "poultry_farm",
        "default_commission_rate",
        "payable_account",
        "is_active",
        "updated_at",
    )
    list_filter = ("seller_type", "is_active", "created_at")
    search_fields = (
        "code",
        "name",
        "contact_name",
        "phone",
        "email",
        "poultry_farm__code",
        "poultry_farm__name",
    )
    raw_id_fields = ("poultry_farm", "payable_account", "created_by")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name", "code")
    list_select_related = ("poultry_farm", "payable_account", "created_by")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SellerProductAssignment)
class SellerProductAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "online_product",
        "seller",
        "farm_display",
        "commission_rate",
        "effective_rate_display",
        "effective_from",
        "is_active",
    )
    list_filter = (
        "is_active",
        "seller__seller_type",
        "online_product__product__business_unit",
    )
    search_fields = (
        "online_product__title",
        "online_product__product__name",
        "online_product__product__product_code",
        "seller__code",
        "seller__name",
        "seller__poultry_farm__code",
        "seller__poultry_farm__name",
    )
    raw_id_fields = ("online_product", "seller")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = (
        "online_product",
        "online_product__product",
        "seller",
        "seller__poultry_farm",
    )

    @admin.display(description="Farm")
    def farm_display(self, obj):
        return obj.seller.poultry_farm or "â€”"

    @admin.display(description="Effective commission")
    def effective_rate_display(self, obj):
        return f"{obj.effective_commission_rate:,.2f}%"


class EcommerceCheckoutOrderInline(admin.TabularInline):
    model = EcommerceCheckoutOrder
    fields = ("business_unit", "order", "amount", "created_at")
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EcommerceCheckout)
class EcommerceCheckoutAdmin(admin.ModelAdmin):
    list_display = (
        "checkout_number",
        "customer_name",
        "customer_phone",
        "user",
        "status",
        "subtotal",
        "discount",
        "tax",
        "total_amount",
        "order_count",
        "created_at",
    )
    list_filter = ("status", "currency", "province", "district", "created_at")
    search_fields = (
        "checkout_number",
        "customer_name",
        "customer_phone",
        "customer_email",
        "delivery_address",
        "checkout_orders__order__order_number",
    )
    raw_id_fields = ("user",)
    readonly_fields = (
        "checkout_number",
        "user",
        "status",
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
        "currency",
        "subtotal",
        "discount",
        "tax",
        "total_amount",
        "created_at",
        "updated_at",
        "completed_at",
    )
    inlines = (EcommerceCheckoutOrderInline,)
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-pk")
    list_select_related = ("user",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .prefetch_related("checkout_orders", "checkout_orders__order")
        )

    @admin.display(description="Orders")
    def order_count(self, obj):
        return obj.checkout_orders.count()

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EcommerceCheckoutOrder)
class EcommerceCheckoutOrderAdmin(admin.ModelAdmin):
    list_display = ("checkout", "business_unit", "order", "amount", "created_at")
    list_filter = ("business_unit", "created_at")
    search_fields = (
        "checkout__checkout_number",
        "checkout__customer_name",
        "order__order_number",
    )
    raw_id_fields = ("checkout", "order")
    readonly_fields = ("checkout", "business_unit", "order", "amount", "created_at")
    ordering = ("-created_at",)
    list_select_related = ("checkout", "order")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EcommercePayment)
class EcommercePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "payment_number",
        "checkout",
        "method",
        "status",
        "amount",
        "provider",
        "provider_reference",
        "confirmed_at",
    )
    list_filter = ("status", "method", "provider", "initiated_at")
    search_fields = (
        "payment_number",
        "checkout__checkout_number",
        "checkout__customer_name",
        "provider_reference",
        "customer_reference",
    )
    raw_id_fields = ("checkout", "customer_advance", "initiated_by", "confirmed_by")
    readonly_fields = (
        "payment_number",
        "checkout",
        "method",
        "status",
        "amount",
        "currency",
        "provider",
        "provider_reference",
        "customer_reference",
        "idempotency_key",
        "proof_image",
        "notes",
        "failure_reason",
        "customer_advance",
        "initiated_by",
        "confirmed_by",
        "initiated_at",
        "confirmed_at",
        "failed_at",
        "refunded_at",
        "updated_at",
    )
    list_select_related = ("checkout", "customer_advance")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MarketplaceOrderLine)
class MarketplaceOrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "product_name",
        "seller",
        "farm",
        "quantity",
        "gross_amount",
        "commission_rate",
        "commission_amount",
        "seller_net_amount",
        "settlement_status",
    )
    list_filter = (
        "settlement_status",
        "seller__seller_type",
        "seller",
        "farm",
        "created_at",
    )
    search_fields = (
        "order_item__order__order_number",
        "product_name",
        "seller_code",
        "seller_name",
        "farm__code",
        "farm__name",
    )
    raw_id_fields = ("order_item", "online_product", "seller", "farm")
    readonly_fields = (
        "order_item",
        "online_product",
        "seller",
        "farm",
        "seller_code",
        "seller_name",
        "product_name",
        "quantity",
        "unit_price",
        "gross_amount",
        "commission_rate",
        "commission_amount",
        "seller_net_amount",
        "settlement_status",
        "eligible_at",
        "created_at",
        "updated_at",
    )
    list_select_related = ("order_item", "order_item__order", "seller", "farm")

    @admin.display(description="Order", ordering="order_item__order__order_number")
    def order_number(self, obj):
        return obj.order_item.order.order_number

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SellerSettlementLineInline(admin.TabularInline):
    model = SellerSettlementLine
    fields = (
        "marketplace_order_line",
        "gross_amount",
        "commission_amount",
        "payable_amount",
        "created_at",
    )
    readonly_fields = fields
    raw_id_fields = ("marketplace_order_line",)
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SellerSettlement)
class SellerSettlementAdmin(admin.ModelAdmin):
    list_display = (
        "settlement_number",
        "seller",
        "status",
        "total_gross",
        "total_commission",
        "total_payable",
        "payment_reference",
        "created_at",
        "paid_at",
    )
    list_filter = ("status", "seller", "created_at", "paid_at")
    search_fields = (
        "settlement_number",
        "seller__code",
        "seller__name",
        "payment_reference",
    )
    raw_id_fields = ("seller", "journal_entry", "created_by", "approved_by", "paid_by")
    readonly_fields = (
        "settlement_number",
        "seller",
        "status",
        "total_gross",
        "total_commission",
        "total_payable",
        "payment_reference",
        "journal_entry",
        "notes",
        "created_by",
        "approved_by",
        "paid_by",
        "created_at",
        "approved_at",
        "paid_at",
        "updated_at",
    )
    inlines = (SellerSettlementLineInline,)
    list_select_related = ("seller", "journal_entry")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SellerSettlementLine)
class SellerSettlementLineAdmin(admin.ModelAdmin):
    list_display = (
        "settlement",
        "marketplace_order_line",
        "gross_amount",
        "commission_amount",
        "payable_amount",
        "created_at",
    )
    search_fields = (
        "settlement__settlement_number",
        "marketplace_order_line__order_item__order__order_number",
        "marketplace_order_line__seller_name",
    )
    raw_id_fields = ("settlement", "marketplace_order_line")
    readonly_fields = (
        "settlement",
        "marketplace_order_line",
        "gross_amount",
        "commission_amount",
        "payable_amount",
        "created_at",
    )
    list_select_related = ("settlement", "marketplace_order_line")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False