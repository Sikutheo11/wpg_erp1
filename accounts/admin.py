from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile

# for Uneditable password
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'last_name','first_name', 'username','phone', 'is_active', 'role',)
    ordering = ('-date_joined',)
    filter_horizontal = ()
    list_filter = ()
    fieldsets = ()

admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
