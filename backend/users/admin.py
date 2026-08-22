from django.contrib import admin
from .models import User, OTP


class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "first_name",
        "last_name",
        "phone_number",
        "username",
    ]


admin.site.register(User, UserAdmin)

admin.site.register(OTP)
