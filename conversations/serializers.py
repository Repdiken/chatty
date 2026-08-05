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
        fields = ["id", "title", "profile_picture"]


class ConversationGroupDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["title", "description", "profile_picture"]


class ConversationPrivateDetailSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "title", "profile_picture"]

        read_only_fields = ["title", "profile_picture"]

    def get_other_user(self, obj):
        """
        Helper method to fetch the other user in the private chat
        so we don't repeat the database query twice.
        """
        current_user = self.context["request"].user

        # Grab the first ConversationMember that is NOT the current user
        other_member = obj.members.exclude(user=current_user).first()

        # Return the actual User instance linked to that member
        if other_member:
            return other_member.user
        return None

    def get_title(self, obj):
        other_user = self.get_other_user(obj)

        if other_user:
            return other_user.username

        return "Unknown User"

    def get_profile_picture(self, obj):
        other_user = self.get_other_user(obj)

        # Check if the user exists AND if they actually uploaded a picture
        if other_user and other_user.profile_picture:
            request = self.context.get("request")
            photo_url = other_user.profile_picture.url

            # build_absolute_uri ensures the frontend gets a full URL (http://127.0.0.1:8000/media/...)
            return request.build_absolute_uri(photo_url) if request else photo_url

        return None
