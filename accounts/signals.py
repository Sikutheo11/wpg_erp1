from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import User, UserProfile
from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group



@receiver(post_save, sender=User)
def post_save_create_profile_receiver(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            profile =UserProfile.objects.get(user=instance)
            profile.save()
        except:
            UserProfile.objects.create(user=instance)

@receiver(pre_save, sender=User)
def pre_save_profile_receiver(sender, instance, **kwargs):
    print('profile created ')

@receiver(post_migrate)
def create_groups(sender, **kwargs):

    groups = [
        "Manager",
        "Carpentry Supervisor",
        "Construction Supervisor",
        "Machinist Supervisor",
        "Carpentry Worker",
        "Construction Worker",
        "Machinist Worker",
        "Finance Manager"
        "Sales",
        "Store Keeper",
        "Accountant",
        "Customer"
    ]

    for group in groups:
        Group.objects.get_or_create(
            name=group
        )