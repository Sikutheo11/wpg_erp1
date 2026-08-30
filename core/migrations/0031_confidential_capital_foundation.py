import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0030_reconcile_system_configuration"),
        ("finance", "0016_finance_integrity_constraints"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CapitalProviderMandate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=40, unique=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("ACTIVE", "Active"), ("PAUSED", "Paused"), ("CLOSED", "Closed")], db_index=True, default="DRAFT", max_length=20)),
                ("minimum_capital", models.DecimalField(decimal_places=2, max_digits=18)),
                ("maximum_capital", models.DecimalField(decimal_places=2, max_digits=18)),
                ("minimum_return_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), help_text="Minimum contractor-agreed return on capital; not actual job profit.", max_digits=7)),
                ("maximum_duration_days", models.PositiveIntegerField()),
                ("preferred_business_units", models.JSONField(blank=True, default=list, help_text="Optional list of business-unit codes accepted by the provider.")),
                ("risk_tolerance", models.CharField(choices=[("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High")], default="MEDIUM", max_length=10)),
                ("requires_controlled_project_account", models.BooleanField(default=False)),
                ("requires_security", models.BooleanField(default=False)),
                ("private_conditions", models.JSONField(blank=True, default=dict, help_text="Internal matching conditions. Never expose directly to contractors.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("capital_provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="capital_provider_mandates", to="finance.counterparty")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_capital_provider_mandates", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [("view_private_capital_provider", "Can view private capital provider details"), ("manage_capital_provider_mandate", "Can manage capital provider mandates")],
            },
        ),
        migrations.CreateModel(
            name="ContractorFundingOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=40, unique=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("VERIFIED", "Verified"), ("MATCHING", "Matching"), ("MATCHED", "Matched"), ("FUNDED", "Funded"), ("CLOSED", "Closed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="DRAFT", max_length=20)),
                ("capital_required", models.DecimalField(decimal_places=2, max_digits=18)),
                ("offered_return_percent", models.DecimalField(decimal_places=2, help_text="Contractor-agreed return percentage on capital requested. It is fixed before funding and is not based on actual net profit.", max_digits=7)),
                ("expected_duration_days", models.PositiveIntegerField()),
                ("security_available", models.BooleanField(default=False)),
                ("controlled_project_account_accepted", models.BooleanField(default=False)),
                ("contractor_costing_snapshot", models.JSONField(blank=True, default=dict, help_text="Private snapshot of contractor estimates used to make the offer. It is not a settlement formula.")),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job_investment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="confidential_funding_offer", to="core.jobinvestment")),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="submitted_contractor_funding_offers", to=settings.AUTH_USER_MODEL)),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_contractor_funding_offers", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [("manage_contractor_funding_offer", "Can manage contractor funding offers"), ("verify_contractor_funding_offer", "Can verify contractor funding offers"), ("view_private_contractor_costing", "Can view private contractor costing")],
            },
        ),
        migrations.CreateModel(
            name="FundingMatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(blank=True, max_length=40, unique=True)),
                ("status", models.CharField(choices=[("CANDIDATE", "Candidate"), ("ADMIN_REVIEW", "Admin review"), ("PROVIDER_INTERESTED", "Provider interested"), ("CONTRACTOR_INTERESTED", "Contractor interested"), ("TERMS", "Terms discussion"), ("APPROVED", "Approved"), ("DECLINED", "Declined"), ("EXPIRED", "Expired")], db_index=True, default="CANDIDATE", max_length=30)),
                ("match_score", models.DecimalField(decimal_places=2, default=Decimal("0.00"), editable=False, max_digits=5)),
                ("score_breakdown", models.JSONField(blank=True, default=dict, editable=False)),
                ("anonymous_opportunity_snapshot", models.JSONField(blank=True, default=dict, help_text="Only sanitized, non-identifying deal information belongs here.")),
                ("provider_identity_disclosed", models.BooleanField(default=False)),
                ("contractor_identity_disclosed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_funding_matches", to=settings.AUTH_USER_MODEL)),
                ("disclosure_approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_capital_match_disclosures", to=settings.AUTH_USER_MODEL)),
                ("job_investment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="confidential_matches", to="core.jobinvestment")),
                ("mandate", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="funding_matches", to="core.capitalprovidermandate")),
            ],
            options={
                "ordering": ["-match_score", "-created_at"],
                "permissions": [("manage_confidential_matching", "Can manage confidential funding matches"), ("approve_identity_disclosure", "Can approve identity disclosure for a match")],
            },
        ),
        migrations.CreateModel(
            name="ProjectAccountControl",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("PROPOSED", "Proposed"), ("BANK_REVIEW", "Bank review"), ("ACTIVE", "Active"), ("SUSPENDED", "Suspended"), ("CLOSED", "Closed")], db_index=True, default="PROPOSED", max_length=20)),
                ("bank_name", models.CharField(max_length=150)),
                ("account_name", models.CharField(max_length=180)),
                ("masked_account_number", models.CharField(help_text="Store a masked/tokenized account reference, not unnecessary bank secrets.", max_length=80)),
                ("signing_rule", models.CharField(choices=[("CONTRACTOR_ONLY", "Contractor only"), ("JOINT", "Contractor + platform jointly"), ("MAKER_CHECKER", "Maker/checker authorization"), ("BANK_CONTROLLED", "Bank-controlled settlement instructions")], default="JOINT", max_length=30)),
                ("platform_approval_required", models.BooleanField(default=True)),
                ("transaction_approval_threshold", models.DecimalField(decimal_places=2, default=Decimal("0.00"), help_text="Payments at or above this amount require the agreed second authorization.", max_digits=18)),
                ("client_payment_directed_here", models.BooleanField(default=False)),
                ("bank_mandate_reference", models.CharField(blank=True, max_length=100)),
                ("bank_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_project_account_controls", to=settings.AUTH_USER_MODEL)),
                ("job_investment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="project_account_control", to="core.jobinvestment")),
            ],
            options={
                "ordering": ["-created_at"],
                "permissions": [("manage_project_account_control", "Can manage project account controls"), ("view_project_bank_details", "Can view controlled project bank details")],
            },
        ),
        migrations.AddConstraint(
            model_name="capitalprovidermandate",
            constraint=models.CheckConstraint(condition=models.Q(("minimum_capital__gt", 0)), name="core_cap_mandate_min_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="capitalprovidermandate",
            constraint=models.CheckConstraint(condition=models.Q(("maximum_capital__gt", 0)), name="core_cap_mandate_max_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="capitalprovidermandate",
            constraint=models.CheckConstraint(condition=models.Q(("minimum_return_percent__gte", 0)), name="core_cap_mandate_return_nonnegative"),
        ),
        migrations.AddConstraint(
            model_name="contractorfundingoffer",
            constraint=models.CheckConstraint(condition=models.Q(("capital_required__gt", 0)), name="core_contractor_offer_capital_gt_zero"),
        ),
        migrations.AddConstraint(
            model_name="contractorfundingoffer",
            constraint=models.CheckConstraint(condition=models.Q(("offered_return_percent__gte", 0), ("offered_return_percent__lte", 100)), name="core_contractor_offer_return_0_100"),
        ),
        migrations.AddConstraint(
            model_name="fundingmatch",
            constraint=models.UniqueConstraint(fields=("job_investment", "mandate"), name="core_unique_job_capital_mandate_match"),
        ),
        migrations.AddConstraint(
            model_name="fundingmatch",
            constraint=models.CheckConstraint(condition=models.Q(("match_score__gte", 0), ("match_score__lte", 100)), name="core_funding_match_score_0_100"),
        ),
        migrations.AddConstraint(
            model_name="projectaccountcontrol",
            constraint=models.CheckConstraint(condition=models.Q(("transaction_approval_threshold__gte", 0)), name="core_project_account_threshold_nonnegative"),
        ),
    ]
