import pytest
from rest_framework.test import APIClient
from users.models import User
from conversations.models import Conversation, ConversationMember

pytestmark = pytest.mark.django_db

# --- FIXTURES ---

@pytest.fixture
def client():
    """Forces the test client to send requests as JSON."""
    client = APIClient()
    client.defaults['HTTP_ACCEPT'] = 'application/json'
    client.defaults['CONTENT_TYPE'] = 'application/json'
    return client

@pytest.fixture
def user1():
    return User.objects.create(username="alice", phone_number="+1234567890")

@pytest.fixture
def user2():
    return User.objects.create(username="bob", phone_number="+1234567891")

@pytest.fixture
def user3():
    return User.objects.create(username="charlie", phone_number="+1234567892")


# --- TESTS ---

class TestConversationCreation:

    def test_group_chat_skips_invalid_users(self, client, user1, user2):
        """Check that a group chat will be created even if a user ID doesn't exist, and skips them."""
        client.force_authenticate(user=user1)
        
        response = client.post("/conversations/create-group", {
            "title": "Project Alpha",
            "usernames": [user2.username, "ghost_user", "fake_user_123"]
        }, format="json")

        assert response.status_code == 201
        # Asserts the view correctly attaches the warning payload
        assert "warning" in response.data
        assert "ghost_user" in response.data["warning"] 

        # Verify the group was created with exactly 2 members (creator + user2)
        conversation = Conversation.objects.first()
        assert conversation.members.count() == 2

    def test_group_chat_with_only_creator(self, client, user1):
        """Check that a single user can make a group chat only with themselves."""
        client.force_authenticate(user=user1)
        
        # Passing an empty list of usernames
        response = client.post("/conversations/create-group", {
            "title": "My Solo Group",
            "usernames": []
        }, format="json")

        assert response.status_code == 201
        
        # Verify the creator is the only member and holds the OWNER role
        conversation = Conversation.objects.first()
        assert conversation.members.count() == 1
        assert conversation.members.first().user == user1
        assert conversation.members.first().role == "owner"

    def test_group_chat_creator_always_included_and_deduplicated(self, client, user1, user2):
        """Check that the creator is always included and duplicates are bypassed."""
        client.force_authenticate(user=user1)
        
        # The user tries to add themselves, and tries to add user2 twice
        response = client.post("/conversations/create-group", {
            "title": "Duplicate Test Group",
            "usernames": [user1.username, user2.username, user2.username]
        }, format="json")

        assert response.status_code == 201
        
        conversation = Conversation.objects.first()
        assert conversation.members.count() == 2  # Just user1 and user2

    def test_cannot_create_private_chat_with_invalid_user(self, client, user1):
        """Users cannot create private chats with users that don't exist."""
        client.force_authenticate(user=user1)
        
        response = client.post("/conversations/create-private", {
            "username": "nobody_exists_here"
        }, format="json")

        # The serializer should raise a ValidationError before creating anything
        assert response.status_code == 400
        assert "User does not exist" in str(response.data)
        assert Conversation.objects.count() == 0


class TestConversationSecurityAndPermissions:

    def test_cannot_change_private_chat_details(self, client, user1, user2):
        """Check that users cannot change the details of a private chat."""
        client.force_authenticate(user=user1)
        client.post("/conversations/create-private", {"username": user2.username}, format="json")
        
        conversation = Conversation.objects.first()
        
        # Attempt to PUT new details to the private chat
        response = client.put(f"/conversations/{conversation.id}", {
            "title": "Hacked Title"
        }, format="json")

        # Assert the ConversationDetailListView blocks this with a 406 status
        assert response.status_code == 406
        assert "Can't change the details" in str(response.data)

    def test_non_members_cannot_access_conversations(self, client, user1, user2, user3):
        """Check that users who are not members of a conversation cannot access its endpoints."""
        # user1 creates a private chat with user2
        client.force_authenticate(user=user1)
        client.post("/conversations/create-private", {"username": user2.username}, format="json")
        conversation = Conversation.objects.first()

        # user3 (who is not in the chat) tries to access it
        client.force_authenticate(user=user3)
        
        get_response = client.get(f"/conversations/{conversation.id}")
        put_response = client.put(f"/conversations/{conversation.id}", {"title": "Sneaky"}, format="json")

        assert get_response.status_code == 404
        assert put_response.status_code == 404


    def test_only_owner_can_delete_group_chat(self, client, user1, user2):
        """Check that only the owner can delete a group chat."""
        # 1. Create a group chat (user1 is automatically the OWNER)
        client.force_authenticate(user=user1)
        client.post("/conversations/create-group", {
            "title": "Deletion Test Group",
            "usernames": [user2.username]
        }, format="json")
        
        conversation = Conversation.objects.first()

        # 2. Switch to user2 (MEMBER) and try to delete it -> Fails
        client.force_authenticate(user=user2)
        response_member = client.delete(f"/conversations/{conversation.id}")
        
        assert response_member.status_code == 403  # Forbidden
        
        # Verify it wasn't accidentally deleted
        conversation.refresh_from_db()
        assert conversation.deleted_at is None

        # 3. Switch back to user1 (OWNER) and delete it -> Succeeds
        client.force_authenticate(user=user1)
        response_owner = client.delete(f"/conversations/{conversation.id}")
        
        assert response_owner.status_code == 204  # 204 No Content is standard for DRF deletes
        
        # Verify the soft delete actually applied the timestamp
        conversation.refresh_from_db()
        assert conversation.deleted_at is not None

    def test_cannot_delete_private_chats(self, client, user1, user2):
        """Check that members cannot delete private chats."""
        # 1. Create a private chat between user1 and user2
        client.force_authenticate(user=user1)
        client.post("/conversations/create-private", {
            "username": user2.username
        }, format="json")
        
        conversation = Conversation.objects.first()

        # 2. user1 tries to delete it -> Fails
        response1 = client.delete(f"/conversations/{conversation.id}")
        assert response1.status_code == 403
        assert "permission" in str(response1.data)

        # 3. Switch to user2 and try to delete it -> Fails
        client.force_authenticate(user=user2)
        response2 = client.delete(f"/conversations/{conversation.id}")
        assert response2.status_code == 403

        # Verify it remained untouched in the database
        conversation.refresh_from_db()
        assert conversation.deleted_at is None



    def test_member_can_leave_private_chat(self, client, user1, user2):
        """Check that a member can successfully leave a private chat."""
        # user1 creates the private chat (both are given the MEMBER role)
        client.force_authenticate(user=user1)
        client.post("/conversations/create-private", {"username": user2.username}, format="json")
        conversation = Conversation.objects.first()

        # user1 decides to leave the chat
        response = client.post(f"/conversations/{conversation.id}/leave")
        
        assert response.status_code == 200
        
        # Verify the soft-delete applied only to user1's membership
        member1 = ConversationMember.objects.get(conversation=conversation, user=user1)
        member2 = ConversationMember.objects.get(conversation=conversation, user=user2)
        
        assert member1.deleted_at is not None  # user1 left
        assert member2.deleted_at is None      # user2 is still in it

    def test_member_can_leave_group_chat(self, client, user1, user2):
        """Check that a regular member can leave a group chat."""
        # user1 creates the group chat (user1 = OWNER, user2 = MEMBER)
        client.force_authenticate(user=user1)
        client.post("/conversations/create-group", {
            "title": "Leave Test Group",
            "usernames": [user2.username]
        }, format="json")
        conversation = Conversation.objects.first()

        # Switch to user2 and leave
        client.force_authenticate(user=user2)
        response = client.post(f"/conversations/{conversation.id}/leave")

        assert response.status_code == 200

        # Verify user2 was soft-deleted from the chat
        member2 = ConversationMember.objects.get(conversation=conversation, user=user2)
        assert member2.deleted_at is not None

    def test_owner_cannot_leave_group_chat(self, client, user1, user2):
        """Check that the owner of a group chat gets blocked from leaving."""
        # user1 creates the group chat (user1 = OWNER)
        client.force_authenticate(user=user1)
        client.post("/conversations/create-group", {
            "title": "Owner Leave Test",
            "usernames": [user2.username]
        }, format="json")
        conversation = Conversation.objects.first()

        # user1 tries to leave their own group -> Fails
        response = client.post(f"/conversations/{conversation.id}/leave")

        assert response.status_code == 403
        assert "cannot leave" in str(response.data).lower()  # Matches our custom error message

        # Verify their membership remains completely active in the database
        member1 = ConversationMember.objects.get(conversation=conversation, user=user1)
        assert member1.deleted_at is None


class TestConversationMemberManagement:

    @pytest.fixture
    def group(self, user1, user2, user3):
        conversation = Conversation.objects.create(
            title="Management test", type=Conversation.Type.GROUP
        )
        ConversationMember.objects.create(
            conversation=conversation, user=user1, role=ConversationMember.Role.OWNER
        )
        ConversationMember.objects.create(
            conversation=conversation, user=user2, role=ConversationMember.Role.ADMIN
        )
        ConversationMember.objects.create(
            conversation=conversation, user=user3, role=ConversationMember.Role.MEMBER
        )
        return conversation

    def member_url(self, group, member):
        return f"/conversations/{group.id}/members/{member.id}"

    def test_only_owner_can_promote_a_member_to_admin(self, client, user1, user2, user3, group):
        member = ConversationMember.objects.get(conversation=group, user=user3)

        client.force_authenticate(user=user2)
        denied = client.patch(
            self.member_url(group, member), {"role": "admin"}, format="json"
        )
        assert denied.status_code == 403

        client.force_authenticate(user=user1)
        allowed = client.patch(
            self.member_url(group, member), {"role": "admin"}, format="json"
        )
        assert allowed.status_code == 200
        member.refresh_from_db()
        assert member.role == ConversationMember.Role.ADMIN

    def test_admin_cannot_remove_owner_or_another_admin(self, client, user1, user2, user3, group):
        owner = ConversationMember.objects.get(conversation=group, user=user1)
        admin = ConversationMember.objects.get(conversation=group, user=user2)
        member = ConversationMember.objects.get(conversation=group, user=user3)
        client.force_authenticate(user=user2)

        assert client.delete(self.member_url(group, owner)).status_code == 403
        assert client.delete(self.member_url(group, admin)).status_code == 403
        assert client.delete(self.member_url(group, member)).status_code == 204
        member.refresh_from_db()
        assert member.deleted_at is not None

    def test_admin_can_edit_group_but_cannot_delete_it(self, client, user1, user2, group):
        client.force_authenticate(user=user2)

        update = client.patch(
            f"/conversations/{group.id}", {"title": "Edited by admin"}, format="json"
        )
        assert update.status_code == 200
        group.refresh_from_db()
        assert group.title == "Edited by admin"

        delete = client.delete(f"/conversations/{group.id}")
        assert delete.status_code == 403
