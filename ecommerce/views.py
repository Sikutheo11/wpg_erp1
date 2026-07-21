from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from .models import OnlineProduct
from inventory.models import Product
from .dashboard import get_ecommerce_dashboard
from django.db.models import Q, F
from .cart import Cart
from .forms import CheckoutForm
from orders.models import Order, OrderItem






# ======================================
# ECOMMERCE DASHBOARD
# ======================================


@login_required
def ecommerce_dashboard(request):

    context = {

        "dashboard":
            get_ecommerce_dashboard(
                request.user
            )

    }


    return render(
        request,
        "ecommerce/dashboard.html",
        context
    )






# ======================================
# ONLINE PRODUCT LIST
# ======================================


@login_required
def online_product_list(request):


    products = OnlineProduct.objects.all()


    return render(
        request,
        "ecommerce/product_list.html",
        {
            "products": products
        }
    )






# ======================================
# CREATE ONLINE PRODUCT
# ======================================


@login_required
def online_product_create(request):


    if request.method == "POST":


        product_id = request.POST.get(
            "product"
        )


        product = get_object_or_404(
            Product,
            id=product_id
        )


        OnlineProduct.objects.create(

            product=product,

            title=request.POST.get(
                "title"
            ),

            short_description=request.POST.get(
                "short_description"
            ),

            description=request.POST.get(
                "description"
            ),

            is_published=
                True if request.POST.get(
                    "is_published"
                )
                else False,


            is_featured=
                True if request.POST.get(
                    "is_featured"
                )
                else False,

        )


        return redirect(
            "ecommerce:online_product_list"
        )



    products = Product.objects.all()



    return render(
        request,
        "ecommerce/product_create.html",
        {
            "products":products
        }
    )






# ======================================
# PRODUCT DETAIL
# ======================================


@login_required
def online_product_detail(
    request,
    slug
):


    product = get_object_or_404(
        OnlineProduct,
        slug=slug
    )


    return render(
        request,
        "ecommerce/product_detail.html",
        {
            "product":product
        }
    )






# ======================================
# PUBLISH / UNPUBLISH
# ======================================


@login_required
def toggle_publish(
    request,
    pk
):


    product = get_object_or_404(
        OnlineProduct,
        pk=pk
    )


    product.is_published = (
        not product.is_published
    )


    product.save()



    return redirect(
        "ecommerce:online_product_list"
    )






# ======================================
# FEATURE / UNFEATURE
# ======================================


@login_required
def toggle_featured(
    request,
    pk
):


    product = get_object_or_404(
        OnlineProduct,
        pk=pk
    )


    product.is_featured = (
        not product.is_featured
    )


    product.save()



    return redirect(
        "ecommerce:online_product_list"
    )

def shop(request):


    products = OnlineProduct.objects.filter(
        is_published=True
    )


    featured = OnlineProduct.objects.filter(
        is_published=True,
        is_featured=True
    )



    context = {

        "products": products,

        "featured_products": featured,

    }



    return render(
        request,
        "ecommerce/shop.html",
        context
    )






# ======================================
# PRODUCT DETAIL PAGE
# ======================================

def product_detail(request, slug):
    """
    Public Product Detail Page
    """

    product = get_object_or_404(
        OnlineProduct,
        slug=slug,
        is_published=True
    )

    # Increment views
    OnlineProduct.objects.filter(
        pk=product.pk
    ).update(
        views=F("views") + 1
    )

    # Refresh object
    product.refresh_from_db()

    # Related products
    related_products = (
        OnlineProduct.objects.filter(
            is_published=True
        )
        .exclude(pk=product.pk)[:4]
    )

    context = {
        "product": product,
        "related_products": related_products,
    }

    return render(
        request,
        "ecommerce/product_detail.html",
        context
    )

def shop(request):


    products = OnlineProduct.objects.filter(
        is_published=True
    )



    # SEARCH

    search = request.GET.get(
        "q"
    )


    if search:

        products = products.filter(

            Q(title__icontains=search)
            |
            Q(product__name__icontains=search)

        )



    featured = OnlineProduct.objects.filter(

        is_published=True,

        is_featured=True

    )



    return render(

        request,

        "ecommerce/shop.html",

        {

            "products":products,

            "featured_products":featured,

            "search":search

        }

    )
def add_to_cart(request, product_id):
    if request.method == "POST":
        cart = Cart(request)
        quantity = request.POST.get("quantity", 1)
        cart.add(product_id, quantity)

    return redirect("ecommerce:cart_detail")


def remove_from_cart(request, product_id):

    cart = Cart(request)

    cart.remove(product_id)

    return redirect("ecommerce:cart_detail")

def cart_detail(request):

    cart = Cart(request)

    items = []

    total = 0

    for product_id, item in cart.cart.items():

        product = OnlineProduct.objects.get(id=product_id)

        quantity = item["quantity"]

        price = float(item["price"])

        subtotal = price * quantity

        total += subtotal

        items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

    return render(request, "ecommerce/cart.html", {
        "items": items,
        "total": total
    })
def update_cart(request, product_id):

    cart = Cart(request)

    if request.method == "POST":

        quantity = request.POST.get("quantity", 1)

        cart.update(product_id, quantity)

    return redirect("ecommerce:cart_detail")
    

@login_required
def checkout(request):

    cart = request.session.get("cart", {})

    if not cart:
        return redirect("ecommerce:cart")

    total = 0
    cart_items = []

    for product_id, item in cart.items():
        subtotal = item["quantity"] * float(item["price"])

        total += subtotal

        cart_items.append({
            "product_id": product_id,
            "quantity": item["quantity"],
            "price": item["price"],
            "subtotal": subtotal,
        })

    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            # ===============================
            # 1. CREATE ORDER
            # ===============================
            order = Order.objects.create(
                user=request.user,
                order_type="ECOMMERCE",
                customer_name=form.cleaned_data["full_name"],
                customer_phone=form.cleaned_data["phone"],
                customer_email=form.cleaned_data["email"],
                province=form.cleaned_data["province"],
                district=form.cleaned_data["district"],
                sector=form.cleaned_data["sector"],
                cell=form.cleaned_data["cell"],
                village=form.cleaned_data["village"],
                delivery_address=form.cleaned_data["delivery_address"],
                notes=form.cleaned_data["notes"],

                subtotal=total,
                discount=0,
                tax=0,
            )
            # ===============================
            # 2. CREATE ORDER ITEMS
            # ===============================
            for item in cart_items:

                OrderItem.objects.create(

                    order=order,

                    product_id=item["product_id"],

                    quantity=item["quantity"],

                    price=item["price"],
                )

            # ===============================
            # 3. CLEAR CART
            # ===============================
            request.session["cart"] = {}
            request.session.modified = True

            # ===============================
            # 4. REDIRECT SUCCESS
            # ===============================
            return redirect("ecommerce:order_success", order_id=order.id)

    else:
        form = CheckoutForm()

    return render(request, "ecommerce/checkout.html", {
        "form": form,
        "total": total,
        "cart_items": cart_items,
    })

def order_success(request, order_id):

    order = Order.objects.get(id=order_id)

    return render(request, "ecommerce/order_success.html", {
        "order": order
    })