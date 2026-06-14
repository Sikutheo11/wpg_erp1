from django.shortcuts import render
from django.db.models import Sum

from .models import Project, Site


def construction_dashboard(request):

    total_projects = Project.objects.count()

    active_projects = Project.objects.filter(
        status='ongoing'
    ).count()

    active_sites = Site.objects.count()

    total_budget = Project.objects.aggregate(
        total=Sum('budget')
    )['total'] or 0

    total_spent = sum(
        project.total_spent for project in Project.objects.all()
    )

    remaining_budget = total_budget - total_spent

    chart_data = []

    for project in Project.objects.all():
        chart_data.append({
            'project': project.name,
            'budget': float(project.budget),
            'spent': float(project.total_spent)
        })

    context = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'active_sites': active_sites,
        'total_budget': total_budget,
        'total_spent': total_spent,
        'remaining_budget': remaining_budget,
        'chart_data': chart_data,
    }

    return render(
        request,
        'construction/dashboard.html',
        context
    )