from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import (
    Order,
    Quotation,
    ProductionMaterial,
    ProductionLabour,
    ProductionMachine,
    ProductionOutput,
    StockReservation,
)

from .forms import (
    OrderForm,
    AssignWorkerForm,
    QuotationForm,
    QuotationApprovalForm,
    ProductionMaterialForm,
    ProductionLabourForm,
    ProductionMachineForm,
    ProductionOutputForm,
    StockReservationForm,
)

from Employee.models import Employee



# =====================================================
# MANAGER DASHBOARD
# =====================================================

@login_required
def furniture_dashboard(request):

    orders = Order.objects.all()

    quotations = Quotation.objects.filter(
        status='submitted'
    )

    context = {

        "orders": orders,

        "total_orders": orders.count(),

        "pending_quotes": quotations.count(),

    }


    return render(
        request,
        "furniture/dashboard.html",
        context
    )




# =====================================================
# CREATE CUSTOMER ORDER
# MANAGER
# =====================================================

@login_required
def order_create(request):

    form = OrderForm(
        request.POST or None
    )


    if request.method == "POST":


        if form.is_valid():

            order = form.save(
                commit=False
            )


            order.created_by = request.user.employee


            order.save()


            messages.success(
                request,
                "Customer order created"
            )


            return redirect(
                "order_list"
            )


    return render(
        request,
        "furniture/order_form.html",
        {
            "form":form
        }
    )




# =====================================================
# ORDER LIST
# =====================================================

@login_required
def order_list(request):

    orders = Order.objects.all()


    return render(
        request,
        "furniture/order_list.html",
        {
            "orders":orders
        }
    )




# =====================================================
# ASSIGN WORKER
# MANAGER
# =====================================================

@login_required
def assign_worker(request, pk):

    order = get_object_or_404(
        Order,
        id=pk
    )


    form = AssignWorkerForm(
        request.POST or None,
        instance=order
    )


    if request.method=="POST":


        if form.is_valid():

            order = form.save()

            order.status="assigned"

            order.save()


            messages.success(
                request,
                "Worker assigned successfully"
            )


            return redirect(
                "order_list"
            )


    return render(
        request,
        "furniture/assign_worker.html",
        {
            "form":form,
            "order":order
        }
    )




# =====================================================
# WORKER QUOTATION CREATE
# =====================================================

@login_required
def create_quotation(request, pk):

    order = get_object_or_404(
        Order,
        id=pk
    )


    quotation, created = Quotation.objects.get_or_create(
        order=order,
        prepared_by=request.user.employee
    )


    form = QuotationForm(
        request.POST or None,
        instance=quotation
    )


    if request.method=="POST":


        if form.is_valid():

            quote=form.save(
                commit=False
            )


            quote.prepared_by=request.user.employee

            quote.status="submitted"

            quote.save()



            order.status="quotation_pending"

            order.save()



            messages.success(
                request,
                "Quotation submitted"
            )


            return redirect(
                "worker_orders"
            )


    return render(
        request,
        "furniture/quotation_form.html",
        {
            "form":form,
            "order":order
        }
    )




# =====================================================
# MANAGER QUOTATION LIST
# =====================================================

@login_required
def quotation_list(request):


    quotations = Quotation.objects.filter(
        status="submitted"
    )


    return render(
        request,
        "furniture/quotation_list.html",
        {
            "quotations":quotations
        }
    )




# =====================================================
# APPROVE QUOTATION
# MANAGER
# =====================================================

@login_required
def approve_quotation(request, pk):

    quotation=get_object_or_404(
        Quotation,
        id=pk
    )


    if request.method=="POST":


        action=request.POST.get(
            "action"
        )


        if action=="approve":


            quotation.status="approved"

            quotation.approved_by=request.user.employee

            quotation.save()



            quotation.order.status="quotation_approved"

            quotation.order.save()



        elif action=="reject":


            quotation.status="rejected"

            quotation.save()



        messages.success(
            request,
            "Quotation updated"
        )


        return redirect(
            "quotation_list"
        )


    return render(
        request,
        "furniture/approve_quotation.html",
        {
            "quotation":quotation
        }
    )




# =====================================================
# ADD MATERIAL CONSUMPTION
# =====================================================

@login_required
def add_material(request, pk):

    order=get_object_or_404(
        Order,
        id=pk
    )


    form=ProductionMaterialForm(
        request.POST or None
    )


    if request.method=="POST":


        if form.is_valid():

            material=form.save(
                commit=False
            )


            material.order=order

            material.save()


            messages.success(
                request,
                "Material added"
            )


            return redirect(
                "order_detail",
                pk
            )



    return render(
        request,
        "furniture/material_form.html",
        {
            "form":form,
            "order":order
        }
    )




# =====================================================
# ADD LABOUR
# =====================================================

@login_required
def add_labour(request, pk):

    order=get_object_or_404(
        Order,
        id=pk
    )


    form=ProductionLabourForm(
        request.POST or None
    )


    if request.method=="POST":

        if form.is_valid():

            labour=form.save(
                commit=False
            )

            labour.order=order

            labour.save()


            return redirect(
                "order_detail",
                pk
            )


    return render(
        request,
        "furniture/labour_form.html",
        {
            "form":form
        }
    )




# =====================================================
# ADD MACHINE
# =====================================================

@login_required
def add_machine(request, pk):

    order=get_object_or_404(
        Order,
        id=pk
    )


    form=ProductionMachineForm(
        request.POST or None
    )


    if request.method=="POST":

        if form.is_valid():

            machine=form.save(
                commit=False
            )

            machine.order=order

            machine.save()


            return redirect(
                "order_detail",
                pk
            )


    return render(
        request,
        "furniture/machine_form.html",
        {
            "form":form
        }
    )




# =====================================================
# PRODUCTION OUTPUT
# =====================================================

@login_required
def add_output(request, pk):

    order=get_object_or_404(
        Order,
        id=pk
    )


    form=ProductionOutputForm(
        request.POST or None
    )


    if request.method=="POST":

        if form.is_valid():

            output=form.save(
                commit=False
            )


            output.order=order

            output.produced_by=request.user.employee

            output.save()


            order.status="completed"

            order.save()


            return redirect(
                "order_list"
            )



    return render(
        request,
        "furniture/output_form.html",
        {
            "form":form
        }
    )

# ==========================================
# MATERIAL LIST
# ==========================================

@login_required
def material_list(request):

    materials = ProductionMaterial.objects.all()


    return render(
        request,
        "furniture/material_list.html",
        {
            "materials":materials
        }
    )




# ==========================================
# LABOUR LIST
# ==========================================

@login_required
def labour_list(request):

    labours = ProductionLabour.objects.all()


    return render(
        request,
        "hr/labour/labour_list.html",
        {
            "labours":labours
        }
    )





# ==========================================
# MACHINE LIST
# ==========================================

@login_required
def machine_list(request):

    machines = ProductionMachine.objects.all()


    return render(
        request,
        "inventory/assets/asset_list.html",
        {
            "machines":machines
        }
    )





# ==========================================
# OUTPUT LIST
# ==========================================

@login_required
def output_list(request):

    outputs = ProductionOutput.objects.all()


    return render(
        request,
        "furniture/output_list.html",
        {
            "outputs":outputs
        }
    )





# ==========================================
# REPORTS
# ==========================================

@login_required
def production_reports(request):


    orders = Order.objects.all()


    total_cost = sum(
        order.quotation.total_cost
        for order in orders
        if hasattr(order,'quotation')
    )


    return render(
        request,
        "furniture/production_reports.html",
        {
            "orders":orders,
            "total_cost":total_cost
        }
    )