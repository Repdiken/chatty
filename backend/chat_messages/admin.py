from django.contrib import admin
from .models import Message


class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "sender", "created_at"]


admin.site.register(Message, MessageAdmin)
