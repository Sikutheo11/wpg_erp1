from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Order
from .forms import RestockOrderForm, RestockOrderItemForm
from .services import OrderService


@login_required
def order_list(request):

    status = request.GET.get("status")

    orders = Order.objects.all().order_by("-created_at")

    if status:
        orders = orders.filter(status=status)

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": orders,
            "status": status,
        }
    )


@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order
        }
    )


@login_required
def update_order_status(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    if request.method == "POST":

        new_status = request.POST.get("status")

        OrderService.update_status(
            order=order,
            new_status=new_status,
            user=request.user
        )

        messages.success(
            request,
            "Order status updated successfully."
        )

    return redirect(
        "orders:order_detail",
        order_id=order.id
    )


@login_required
def restock_order_create(request):

    order_form = RestockOrderForm(request.POST or None)
    item_form = RestockOrderItemForm(request.POST or None)

    if request.method == "POST":

        if order_form.is_valid() and item_form.is_valid():

            order = order_form.save(commit=False)

            order.user = request.user
            order.order_type = "PRODUCTION"
            order.status = "PENDING"

            order.save()

            item = item_form.save(commit=False)

            item.order = order
            item.product_name = item.product.name

            item.save()

            order.subtotal = item.subtotal
            order.save()

            job = OrderService.create_production_job_from_order(
                order=order,
                user=request.user
            )

            messages.success(
                request,
                "Restock order and production job created successfully."
            )

            return redirect(
                "furniture:production_job_detail",
                pk=job.id
            )

        messages.error(
            request,
            "Please correct the errors below."
        )

    return render(
        request,
        "orders/restock_order_form.html",
        {
            "order_form": order_form,
            "item_form": item_form,
        }
    )


@login_required
def create_production_job(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    job = OrderService.create_production_job_from_order(
        order=order,
        user=request.user
    )

    messages.success(
        request,
        "Production job created successfully."
    )

    return redirect(
        "furniture:production_job_detail",
        pk=job.id
    )