from django.urls import path

from . import views


app_name = "agriculture"


urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Farms and poultry houses
    path("farms/", views.farm_list, name="farm_list"),
    path("farms/new/", views.farm_create, name="farm_create"),
    path("farms/<int:pk>/", views.farm_detail, name="farm_detail"),
    path("farms/<int:pk>/edit/", views.farm_update, name="farm_update"),
    path(
        "farms/<int:farm_pk>/houses/new/",
        views.house_create,
        name="farm_house_create",
    ),
    path("houses/new/", views.house_create, name="house_create"),

    # Poultry breeds
    path("breeds/", views.breed_list, name="breed_list"),
    path("breeds/new/", views.breed_create, name="breed_create"),

    # Agriculture operations and Core workflow
    path("operations/", views.operation_list, name="operation_list"),
    path(
        "operations/new/",
        views.operation_create,
        name="operation_create",
    ),
    path(
        "operations/<int:pk>/",
        views.operation_detail,
        name="operation_detail",
    ),
    path(
        "operations/<int:pk>/<str:action>/",
        views.operation_action,
        name="operation_action",
    ),

    # Poultry flocks
    path("flocks/", views.flock_list, name="flock_list"),
    path("flocks/new/", views.flock_create, name="flock_create"),
    path("flocks/<int:pk>/", views.flock_detail, name="flock_detail"),

    # Flock operational records
    path(
        "flocks/<int:flock_pk>/daily-records/new/",
        views.daily_record_create,
        name="daily_record_create",
    ),
    path(
        "flocks/<int:flock_pk>/egg-production/new/",
        views.egg_production_create,
        name="egg_production_create",
    ),
    path(
        "flocks/<int:flock_pk>/feeding/new/",
        views.feeding_record_create,
        name="feeding_record_create",
    ),
    path(
        "flocks/<int:flock_pk>/health/new/",
        views.health_record_create,
        name="health_record_create",
    ),
    path(
        "flocks/<int:flock_pk>/mortality/new/",
        views.mortality_record_create,
        name="mortality_record_create",
    ),

    # Incubation
    path("incubation/", views.incubation_list, name="incubation_list"),
    path(
        "incubation/new/",
        views.incubation_create,
        name="incubation_create",
    ),
    path(
        "incubation/<int:pk>/",
        views.incubation_detail,
        name="incubation_detail",
    ),
    path(
        "incubation/<int:pk>/candle/",
        views.incubation_candle,
        name="incubation_candle",
    ),
    path(
        "incubation/<int:pk>/complete/",
        views.incubation_complete,
        name="incubation_complete",
    ),

    # Valuation and management reports
    path(
        "reports/valuation/",
        views.valuation_report,
        name="valuation_report",
    ),
    path(
        "houses/<int:pk>/edit/",
        views.house_update,
        name="house_update",
    ),
]
