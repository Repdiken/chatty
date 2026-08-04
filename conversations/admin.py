from django.contrib import admin
from .models import ConversationMember, Conversation


class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "type", "title", "created_at"]


admin.site.register(Conversation, ConversationAdmin)


admin.site.register(ConversationMember)
