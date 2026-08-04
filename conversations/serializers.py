from rest_framework import serializers
from .models import ConversationMember, Conversation
from users.models import User


class ConversationPrivateCreateSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")

        return user


class ConversationGroupCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=55)
    usernames = serializers.ListField(
        child=serializers.CharField(), max_length=30, allow_empty=True
    )

    def validate_usernames(self, value):
        request_user = self.context["request"].user
        # set() creates a set object, a collection of unique elements
        unique_usernames = set(value)
        unique_usernames.discard(request_user.username)
        # single SQL query: SELECT ... WHERE username IN ('user1', 'user2')
        valid_users = User.objects.filter(username__in=unique_usernames)
        valid_usernames_set = set(valid_users.values_list("username", flat=True))
        invalid_usernames = unique_usernames - valid_usernames_set

        return {
            "valid_users": valid_users,
            "invalid_users": list(invalid_usernames),
        }


class ConversationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["title", "profile_picture"]
