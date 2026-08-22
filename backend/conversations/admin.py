from django.contrib import admin
from .models import ConversationMember, Conversation


class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "type", "title", "created_at", "deleted_at"]


admin.site.register(Conversation, ConversationAdmin)


class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "conversation", "role"]


admin.site.register(ConversationMember, ConversationMemberAdmin)
