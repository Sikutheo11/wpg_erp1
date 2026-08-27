from django.urls import path

from . import job_investment_views

urlpatterns = [
    path("orders/<int:order_pk>/open/", job_investment_views.job_investment_open, name="job_investment_open"),
    path("<int:pk>/", job_investment_views.job_investment_detail, name="job_investment_detail"),
    path("<int:pk>/refresh/", job_investment_views.job_investment_refresh, name="job_investment_refresh"),
    path("<int:pk>/wpg-capital/", job_investment_views.job_investment_update_wpg_capital, name="job_investment_update_wpg_capital"),
    path("<int:pk>/agreements/add/", job_investment_views.job_investment_add_agreement, name="job_investment_add_agreement"),
    path("agreements/<int:agreement_pk>/approve/", job_investment_views.job_investment_approve_agreement, name="job_investment_approve_agreement"),
    path("<int:pk>/contributions/add/", job_investment_views.job_investment_add_contribution, name="job_investment_add_contribution"),
    path("<int:pk>/actual-result/", job_investment_views.job_investment_update_actual_result, name="job_investment_update_actual_result"),
    path("agreements/<int:agreement_pk>/settlement/", job_investment_views.job_investment_prepare_settlement, name="job_investment_prepare_settlement"),
    path("<int:pk>/finance/income/", job_investment_views.job_investment_link_income, name="job_investment_link_income"),
    path("<int:pk>/finance/expense/", job_investment_views.job_investment_link_expense, name="job_investment_link_expense"),
    path("<int:pk>/finance/sync/", job_investment_views.job_investment_sync_finance, name="job_investment_sync_finance"),
    path("agreements/<int:agreement_pk>/post-settlement/", job_investment_views.job_investment_post_settlement, name="job_investment_post_settlement"),
    path("settlements/<int:settlement_pk>/sync-repayment/", job_investment_views.job_investment_sync_repayment, name="job_investment_sync_repayment"),
    path("<int:pk>/sync-repayments/", job_investment_views.job_investment_sync_all_repayments, name="job_investment_sync_all_repayments"),
]
