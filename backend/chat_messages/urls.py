from django.urls import path
from .views import ListCreateMessageAPIView
from django.urls import re_path
from . import consumers

urlpatterns = [
    path(
        "conversations/<int:conversation_id>/messages",
        ListCreateMessageAPIView.as_view(),
    )
]

websocket_urlpatterns = [
    re_path(
        r"ws/conversations/(?P<conversation_id>\d+)/$", consumers.ChatConsumer.as_asgi()
    ),
]
