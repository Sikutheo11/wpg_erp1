from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from core.event_engine import EventEngine

from ..models import Customer


class CustomerService:
    """
    Business logic for Sales Engine customers.

    Responsibilities:
    - create and update customer records;
    - validate customer identity and credit limits;
    - search active and inactive customers;
    - activate or deactivate customers;
    - detect likely duplicate customers;
    - safely merge duplicate customer records.
    """

    @staticmethod
    def _decimal(value):
        return Decimal(str(value or 0))

    @staticmethod
    def _user(actor):
        if actor is None:
            return None

        if hasattr(actor, "is_authenticated"):
            return actor

        return getattr(actor, "user", None)

    @staticmethod
    def _clean_text(value):
        return (value or "").strip()

    @classmethod
    def _validate_customer_type(cls, customer_type):
        valid_types = {
            value
            for value, label in Customer.CUSTOMER_TYPES
        }

        if customer_type not in valid_types:
            raise ValidationError(
                "Invalid customer type."
            )

        return customer_type

    @classmethod
    def _validate_identity(
        cls,
        *,
        full_name="",
        company_name="",
        user=None,
    ):
        full_name = cls._clean_text(full_name)
        company_name = cls._clean_text(company_name)

        if not full_name and not company_name and user is None:
            raise ValidationError(
                (
                    "Provide a full name, company name "
                    "or linked user account."
                )
            )

        return full_name, company_name

    @classmethod
    def _validate_credit_limit(cls, credit_limit):
        credit_limit = cls._decimal(
            credit_limit
        )

        if credit_limit < 0:
            raise ValidationError(
                "Credit limit cannot be negative."
            )

        return credit_limit

    @classmethod
    def find_duplicates(
        cls,
        *,
        phone="",
        email="",
        user=None,
        exclude_customer=None,
    ):
        """
        Return likely duplicate customers based on phone, email or user.
        """

        phone = cls._clean_text(phone)
        email = cls._clean_text(email)

        query = Q()

        if phone:
            query |= Q(
                phone__iexact=phone
            )

        if email:
            query |= Q(
                email__iexact=email
            )

        if user is not None:
            query |= Q(
                user=user
            )

        if not query:
            return Customer.objects.none()

        queryset = Customer.objects.filter(
            query
        )

        if exclude_customer is not None:
            queryset = queryset.exclude(
                pk=exclude_customer.pk
            )

        return queryset

    @classmethod
    @transaction.atomic
    def create_customer(
        cls,
        *,
        customer_type="INDIVIDUAL",
        full_name="",
        company_name="",
        phone,
        email="",
        address="",
        tax_number="",
        credit_limit=0,
        user=None,
        is_active=True,
        actor=None,
        allow_duplicate=False,
    ):
        customer_type = cls._validate_customer_type(
            customer_type
        )

        full_name, company_name = (
            cls._validate_identity(
                full_name=full_name,
                company_name=company_name,
                user=user,
            )
        )

        phone = cls._clean_text(
            phone
        )

        if not phone:
            raise ValidationError(
                "Customer phone is required."
            )

        email = cls._clean_text(
            email
        )

        address = cls._clean_text(
            address
        )

        tax_number = cls._clean_text(
            tax_number
        )

        credit_limit = cls._validate_credit_limit(
            credit_limit
        )

        duplicates = cls.find_duplicates(
            phone=phone,
            email=email,
            user=user,
        )

        if duplicates.exists() and not allow_duplicate:
            duplicate = duplicates.first()

            raise ValidationError(
                (
                    "A customer with the same phone, email "
                    f"or user already exists: {duplicate}."
                )
            )

        customer = Customer.objects.create(
            user=user,
            customer_type=customer_type,
            full_name=full_name,
            company_name=company_name,
            phone=phone,
            email=email,
            address=address,
            tax_number=tax_number,
            credit_limit=credit_limit,
            is_active=is_active,
        )

        customer.full_clean()

        EventEngine.dispatch(
            event_code="SALES_CUSTOMER_CREATED",
            actor=cls._user(actor),
            obj=customer,
            title="Customer Created",
            message=(
                f"Customer {customer.display_name} "
                "was created."
            ),
            level="INFO",
            metadata={
                "customer_id": customer.pk,
                "customer_type": (
                    customer.customer_type
                ),
                "full_name": customer.full_name,
                "company_name": (
                    customer.company_name
                ),
                "phone": customer.phone,
                "email": customer.email,
                "credit_limit": str(
                    customer.credit_limit
                ),
                "is_active": customer.is_active,
                "linked_user_id": (
                    customer.user_id
                ),
            },
            notify_groups=[
                "Sales Manager",
            ],
            notify_owner=True,
        )

        return customer

    @classmethod
    @transaction.atomic
    def update_customer(
        cls,
        *,
        customer,
        customer_type=None,
        full_name=None,
        company_name=None,
        phone=None,
        email=None,
        address=None,
        tax_number=None,
        credit_limit=None,
        user=None,
        update_user=False,
        is_active=None,
        actor=None,
        allow_duplicate=False,
    ):
        if customer is None:
            raise ValidationError(
                "Customer is required."
            )

        if not isinstance(
            customer,
            Customer,
        ):
            raise ValidationError(
                "A valid Customer instance is required."
            )

        if customer_type is not None:
            customer.customer_type = (
                cls._validate_customer_type(
                    customer_type
                )
            )

        if full_name is not None:
            customer.full_name = cls._clean_text(
                full_name
            )

        if company_name is not None:
            customer.company_name = cls._clean_text(
                company_name
            )

        if phone is not None:
            customer.phone = cls._clean_text(
                phone
            )

        if not customer.phone:
            raise ValidationError(
                "Customer phone is required."
            )

        if email is not None:
            customer.email = cls._clean_text(
                email
            )

        if address is not None:
            customer.address = cls._clean_text(
                address
            )

        if tax_number is not None:
            customer.tax_number = cls._clean_text(
                tax_number
            )

        if credit_limit is not None:
            customer.credit_limit = (
                cls._validate_credit_limit(
                    credit_limit
                )
            )

        if update_user:
            customer.user = user

        if is_active is not None:
            customer.is_active = bool(
                is_active
            )

        cls._validate_identity(
            full_name=customer.full_name,
            company_name=customer.company_name,
            user=customer.user,
        )

        duplicates = cls.find_duplicates(
            phone=customer.phone,
            email=customer.email,
            user=customer.user,
            exclude_customer=customer,
        )

        if duplicates.exists() and not allow_duplicate:
            duplicate = duplicates.first()

            raise ValidationError(
                (
                    "Another customer with the same phone, "
                    f"email or user exists: {duplicate}."
                )
            )

        customer.full_clean()
        customer.save()

        EventEngine.dispatch(
            event_code="SALES_CUSTOMER_UPDATED",
            actor=cls._user(actor),
            obj=customer,
            title="Customer Updated",
            message=(
                f"Customer {customer.display_name} "
                "was updated."
            ),
            level="INFO",
            metadata={
                "customer_id": customer.pk,
                "customer_type": (
                    customer.customer_type
                ),
                "phone": customer.phone,
                "email": customer.email,
                "credit_limit": str(
                    customer.credit_limit
                ),
                "is_active": customer.is_active,
                "linked_user_id": (
                    customer.user_id
                ),
            },
            notify_groups=[
                "Sales Manager",
            ],
            notify_owner=True,
        )

        return customer

    @classmethod
    def search_customers(
        cls,
        *,
        query="",
        active_only=True,
        customer_type=None,
    ):
        queryset = Customer.objects.select_related(
            "user"
        )

        if active_only:
            queryset = queryset.filter(
                is_active=True
            )

        if customer_type:
            queryset = queryset.filter(
                customer_type=customer_type
            )

        query = cls._clean_text(
            query
        )

        if query:
            queryset = queryset.filter(
                Q(full_name__icontains=query)
                | Q(company_name__icontains=query)
                | Q(phone__icontains=query)
                | Q(email__icontains=query)
                | Q(tax_number__icontains=query)
                | Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
            )

        return queryset.order_by(
            "company_name",
            "full_name",
            "phone",
        )

    @classmethod
    @transaction.atomic
    def deactivate_customer(
        cls,
        *,
        customer,
        actor=None,
    ):
        if customer is None:
            raise ValidationError(
                "Customer is required."
            )

        customer.is_active = False

        customer.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="SALES_CUSTOMER_DEACTIVATED",
            actor=cls._user(actor),
            obj=customer,
            title="Customer Deactivated",
            message=(
                f"Customer {customer.display_name} "
                "was deactivated."
            ),
            level="WARNING",
            metadata={
                "customer_id": customer.pk,
            },
            notify_groups=[
                "Sales Manager",
            ],
            notify_owner=True,
        )

        return customer

    @classmethod
    @transaction.atomic
    def activate_customer(
        cls,
        *,
        customer,
        actor=None,
    ):
        if customer is None:
            raise ValidationError(
                "Customer is required."
            )

        customer.is_active = True

        customer.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="SALES_CUSTOMER_ACTIVATED",
            actor=cls._user(actor),
            obj=customer,
            title="Customer Activated",
            message=(
                f"Customer {customer.display_name} "
                "was activated."
            ),
            level="SUCCESS",
            metadata={
                "customer_id": customer.pk,
            },
            notify_groups=[
                "Sales Manager",
            ],
            notify_owner=True,
        )

        return customer

    @classmethod
    @transaction.atomic
    def update_credit_limit(
        cls,
        *,
        customer,
        credit_limit,
        actor=None,
    ):
        if customer is None:
            raise ValidationError(
                "Customer is required."
            )

        customer.credit_limit = (
            cls._validate_credit_limit(
                credit_limit
            )
        )

        customer.save(
            update_fields=[
                "credit_limit",
                "updated_at",
            ]
        )

        EventEngine.dispatch(
            event_code="SALES_CUSTOMER_CREDIT_LIMIT_UPDATED",
            actor=cls._user(actor),
            obj=customer,
            title="Customer Credit Limit Updated",
            message=(
                f"Credit limit for {customer.display_name} "
                f"was set to {customer.credit_limit} RWF."
            ),
            level="INFO",
            metadata={
                "customer_id": customer.pk,
                "credit_limit": str(
                    customer.credit_limit
                ),
            },
            notify_groups=[
                "Sales Manager",
                "Finance Manager",
            ],
            notify_owner=True,
        )

        return customer

    @classmethod
    @transaction.atomic
    def merge_customers(
        cls,
        *,
        primary_customer,
        duplicate_customer,
        actor=None,
        deactivate_duplicate=True,
    ):
        """
        Move quotation and legacy sale relations to the primary customer.

        This method does not delete the duplicate record. It can deactivate
        it after moving related records.
        """

        if primary_customer is None or duplicate_customer is None:
            raise ValidationError(
                (
                    "Primary and duplicate customers "
                    "are required."
                )
            )

        if primary_customer.pk == duplicate_customer.pk:
            raise ValidationError(
                "A customer cannot be merged into itself."
            )

        duplicate_customer.quotations.update(
            customer=primary_customer
        )

        if hasattr(
            duplicate_customer,
            "sales",
        ):
            duplicate_customer.sales.update(
                customer=primary_customer
            )

        if (
            not primary_customer.user
            and duplicate_customer.user
        ):
            primary_customer.user = (
                duplicate_customer.user
            )

        if (
            not primary_customer.email
            and duplicate_customer.email
        ):
            primary_customer.email = (
                duplicate_customer.email
            )

        if (
            not primary_customer.address
            and duplicate_customer.address
        ):
            primary_customer.address = (
                duplicate_customer.address
            )

        if (
            not primary_customer.tax_number
            and duplicate_customer.tax_number
        ):
            primary_customer.tax_number = (
                duplicate_customer.tax_number
            )

        if (
            duplicate_customer.credit_limit
            > primary_customer.credit_limit
        ):
            primary_customer.credit_limit = (
                duplicate_customer.credit_limit
            )

        primary_customer.full_clean()
        primary_customer.save()

        if deactivate_duplicate:
            duplicate_customer.is_active = False

            duplicate_customer.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

        EventEngine.dispatch(
            event_code="SALES_CUSTOMERS_MERGED",
            actor=cls._user(actor),
            obj=primary_customer,
            title="Customers Merged",
            message=(
                f"Customer {duplicate_customer.pk} "
                f"was merged into customer "
                f"{primary_customer.pk}."
            ),
            level="WARNING",
            metadata={
                "primary_customer_id": (
                    primary_customer.pk
                ),
                "duplicate_customer_id": (
                    duplicate_customer.pk
                ),
                "duplicate_deactivated": (
                    deactivate_duplicate
                ),
            },
            notify_groups=[
                "Sales Manager",
            ],
            notify_owner=True,
        )

        return primary_customer
