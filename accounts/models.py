from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


# =====================================================
# USER MANAGER
# =====================================================

class UserManager(BaseUserManager):

    def create_user(
        self,
        email,
        username,
        first_name,
        last_name,
        password=None
    ):

        if not email:
            raise ValueError("User must have email address")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        username,
        first_name,
        last_name,
        password=None
    ):

        user = self.create_user(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password
        )

        user.role = 'admin'
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True

        user.save(using=self._db)

        return user


# =====================================================
# USER
# =====================================================

class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('worker', 'Worker'),
        ('customer', 'Customer'),
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    username = models.CharField(
        max_length=50,
        unique=True
    )

    email = models.EmailField(
        max_length=100,
        unique=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        null=True
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    created_date = models.DateTimeField(
        auto_now_add=True
    )

    modified_date = models.DateTimeField(
        auto_now=True
    )

    is_admin = models.BooleanField(
        default=False
    )

    is_staff = models.BooleanField(
        default=False
    )

    is_active = models.BooleanField(
        default=True
    )

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = [
        'username',
        'first_name',
        'last_name'
    ]

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()

    # ==========================================
    # ROLE HELPERS
    # ==========================================

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_worker(self):
        return self.role == 'worker'

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_admin_user(self):
        return self.role == 'admin'

    # ==========================================
    # DJANGO PERMISSIONS
    # ==========================================

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True


# =====================================================
# USER PROFILE
# =====================================================

class UserProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    picture_profile = models.ImageField(
        upload_to='users/profile_pictures',
        blank=True,
        null=True
    )

    cover_photo = models.ImageField(
        upload_to='users/cover_photos',
        blank=True,
        null=True
    )

    country = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    province = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    district = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    sector = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    cell = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    village = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    personal_id = models.CharField(
        max_length=20,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    modified_date = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return self.user.email