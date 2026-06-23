from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User, UserProfile
from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:

        UserProfile.objects.get_or_create(
            user=instance
        )

@receiver(post_migrate)
def create_groups(sender, **kwargs):

    groups = [
    "Administrator",
    "Manager",
    "Finance Manager",
    "HR Manager",
    "Production Supervisor",
    "Carpentry Supervisor",
    "Construction Supervisor",
    "Machinist Supervisor",
    "Carpentry Worker",
    "Construction Worker",
    "Machinist Worker",
    "Sales Officer",
    "Store Keeper",
    "Accountant",
    "Customer",
]

    for group in groups:
        Group.objects.get_or_create(
            name=group
        )