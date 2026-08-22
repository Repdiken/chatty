# Chatty

> **Status: Under Development 🚧**
>
> Chatty is a Django-based messaging application that I am building from scratch as a backend-development project. The project is **not finished** and several planned features are still being implemented.

## Overview

Chatty is designed around a phone-number-first authentication system and a messaging backend.

The current design uses:

- **Django**
- **Django REST Framework**
- **Simple JWT**
- OTP-based authentication
- Optional username-based user discovery
- Optional password-based two-step verification
- Conversations with private and group chat types
- Conversation membership and roles
- A REST API for user and conversation management
- Django Channels/WebSocket support planned for real-time messaging

The goal is to build the backend first and gradually add the frontend and real-time chat functionality.

---

## Current Authentication Design

Chatty does **not** use a traditional username/password login as its primary authentication method.

### Primary authentication

The main authentication flow is:

```text
Phone number
      ↓
Request OTP
      ↓
Receive OTP
      ↓
Submit OTP
      ↓
JWT access + refresh tokens
```

For registration:

```text
Phone number
      ↓
Request registration OTP
      ↓
Verify OTP
      ↓
Create User
      ↓
JWT access + refresh tokens
```

For login:

```text
Phone number
      ↓
Request login OTP
      ↓
Verify OTP
      ↓
JWT access + refresh tokens
```

### Optional two-step verification

Users can optionally configure a password for an additional authentication step.

The password is **not** the primary login mechanism. OTP remains the main authentication method.

Passwords are handled using Django's password hashing system:

- `set_password()` when storing/changing a password
- `check_password()` / `user.check_password()` when verifying a password
- Django's password validators for password requirements

Passwords are never stored as plain text.

---

## OTP Security

The OTP system currently implements:

- Six-digit OTP generation
- OTP hashing before storage
- Three-minute OTP expiration
- OTP attempt tracking
- Lockout after three failed OTP attempts
- Thirty-minute lockout period
- Lockout checks when requesting and verifying OTPs
- Lockout state reset after the lockout period expires
- Separate registration and login OTP flows
- Existing-account checks during registration
- Existing-account checks during login

The OTP is currently returned in the API response for development/testing purposes.

> **Important:** Returning the OTP in an API response is only suitable for development/testing. A production implementation should send the OTP through an actual SMS provider and never expose it through the API response.

---

# User System

The custom `User` model is designed around the phone number as the primary identifier.

The user profile is intended to support:

- Phone number
- Username
- First name
- Last name
- Profile picture
- Bio
- Optional password for two-step verification
- Online/offline status
- Last-seen information
- Soft deletion

### Username

Username is optional and can be configured after registration.

The username is intended to be used for user discovery and conversation creation.

Username handling is intended to be case-insensitive, so values such as:

```text
@Amir
@amir
@AMIR
```

should resolve to the same username.

---

# Conversation System

Chatty separates conversations from their members.

The main entities are:

```text
Conversation
      │
      └── ConversationMember
                │
                └── User
```

This allows a conversation to have multiple users and allows roles to be assigned to members.

### Conversation types

There are currently two planned/implemented conversation types:

- `private`
- `group`

### Private conversations

A private conversation contains two users.

When viewing a private conversation, the conversation itself does not need to store a title or profile picture.

Instead, the API can return the **other participant's**:

- username/name as the conversation title
- profile picture

For example:

```text
Amir ↔ Alice
```

When Amir requests the conversation:

```json
{
    "title": "Alice",
    "profile_picture": "..."
}
```

When Alice requests the same conversation:

```json
{
    "title": "Amir",
    "profile_picture": "..."
}
```

### Group conversations

Groups have their own:

- title
- description
- profile picture

Group details can be changed by users with the appropriate permissions, such as the owner/admin.

---

# Conversation Members

`ConversationMember` represents the relationship between a user and a conversation.

Members can have roles such as:

- Owner
- Admin
- Member

The relationship also stores information such as:

- Joined time
- Deleted/removed state

A unique constraint prevents the same user from being added to the same conversation more than once.

---

# Authorization

Authenticated API requests use JWT authentication.

Conversation access is also restricted by membership.

A user should only be able to access a conversation if they are a member of that conversation.

Conversation-management permissions are intended to distinguish between:

- normal members
- administrators
- owners

For example, changing group details should not be available to ordinary members.

---

# API Endpoints

The following are the endpoints currently implemented/planned in the project based on the current API design.

## Authentication

### Register — Request OTP

```http
POST /auth/register/request-otp
```

Request:

```json
{
    "phone_number": "+905XXXXXXXXX"
}
```

Purpose:

- Validate the phone number
- Check that an account does not already exist
- Generate an OTP
- Hash and store the OTP
- Set the three-minute expiration
- Return the OTP during development

---

### Register — Verify OTP and Create Account

```http
POST /auth/register/verify/
```

Request:

```json
{
    "phone_number": "+905XXXXXXXXX",
    "otp": "123456"
}
```

Purpose:

- Find the current OTP
- Check expiration
- Check lockout state
- Validate the OTP
- Track failed attempts
- Lock the OTP after three failed attempts
- Create the user after successful verification
- Return JWT access and refresh tokens

---

### Login — Request OTP

```http
POST /auth/login/request-otp
```

Request:

```json
{
    "phone_number": "+905XXXXXXXXX"
}
```

Purpose:

- Check that an account exists
- Generate a new OTP
- Store the hashed OTP
- Set the expiration time
- Return the OTP during development

---

### Login — Verify OTP and Get Tokens

```http
POST /auth/login/verify/
```

Request:

```json
{
    "phone_number": "+905XXXXXXXXX",
    "otp": "123456"
}
```

Purpose:

- Validate the OTP
- Check expiration
- Check lockout state
- Track failed attempts
- Return JWT access and refresh tokens

---

# User/Profile Endpoints

The project currently includes endpoints for managing the authenticated user's profile and account information.

### Complete Profile

```http
GET/PATCH /users/me/about/
```

Used to retrieve or update profile information such as:

- First name
- Last name
- Profile picture
- Bio
- Username
- Phone number, where appropriate

The authenticated user is obtained from:

```python
request.user
```

rather than allowing the client to select another user's ID.

---

### Change Phone Number

```http
PATCH /users/me/about/phone-number-change/ | /users/me/about/phone-number-change/verify/
```

Changing a phone number requires verification of the new number.

The intended flow is to reuse the OTP verification mechanism rather than simply changing the phone number immediately.

After changing the phone number, the authentication tokens should be rotated/reissued so that the old authentication state can be invalidated.

---

### Set Username

```http
PATCH /users/me/about/username-change/
```

Used to set or change the optional username.

The username is unique and is intended to be normalized for case-insensitive lookup.

---

### Set Password / Enable Two-Step Verification

```http
PATCH /users/me/security/2fa/ | users/me/security/2fa/remove
```

Used to create or set the optional two-step verification password.

Used when a user already has a password and wants to replace it.

The password is validated with Django's password validation framework and stored using Django's password hashing system.

The current password is checked using Django's password-checking mechanism rather than comparing the plain-text password with the database value.

---

# Conversation Endpoints

## Create Private Conversation

```http
POST /conversations/create-private/
```

The client provides the username of the user they want to chat with.

A private conversation contains exactly two members.

---

## Create Group Conversation

```http
POST /conversations/create-group/
```

The client provides the users who should initially belong to the group.

The backend validates each user and prevents duplicate members.

---

## Conversation Details

```http
GET /conversations/{conversation_id}/
```

Returns the details of a conversation.

The endpoint checks that the authenticated user is a member of the requested conversation.

For private conversations, the response represents the other participant rather than returning empty conversation-level title/profile fields.

---

## Update Group Details

```http
PATCH /conversations/{conversation_id}/
```

Used to update group information such as:

- Title
- Description
- Profile picture

This is not available for private conversations.

The operation is restricted according to conversation-management permissions.

---

## Delete Conversation

```http
DELETE /conversations/{conversation_id}/
```

Used for group conversation deletion behavior.

---

# Leave Conversation

```http
PUT /conversations/{conversation_id}/leave/
```

Used for leaving a conversation.

Group owners cannot leave the group chat unless the transfer the ownership.

---

## Conversation Messages

```http
GET /conversations/{conversation_id}/messages/
```

This endpoint is intended to return the message history for a conversation.

Access should be restricted to conversation members.

---

# Authentication with Postman

During development, the easiest way to test authenticated endpoints is with Postman.

After successfully registering or logging in, the API returns:

```json
{
    "access": "YOUR_ACCESS_TOKEN",
    "refresh": "YOUR_REFRESH_TOKEN"
}
```

Copy the **access token**.

For every authenticated request, send it in the HTTP header:

```http
Authorization: JWT YOUR_ACCESS_TOKEN
```

### Postman

In Postman:

1. Select the request.
2. Open the **Authorization** tab.
3. Select **Bearer Token**.
4. Paste the access token into the token field.
5. Send the request.

Alternatively, you can manually add:

```text
Authorization: JWT <access_token>
```

to the request headers.

You can also use a browser header editor while testing authenticated API requests from the browser.

> The access token should not be manually copied into every request forever. A real frontend will normally store/manage the authentication state and automatically attach the token to authenticated API requests.

---

# Running the Project

## 1. Clone the repository

```bash
git clone <repository-url>
cd Chatty
```

## 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

Copy:

```text
.env.example
```

to:

```text
.env
```

Then configure the required environment variables for your local environment.

Do not commit the real `.env` file or secrets to Git.

## 5. Apply migrations

```bash
python manage.py migrate
```

## 6. Create an admin account

```bash
python manage.py createsuperuser
```

## 7. Start the development server

```bash
python manage.py runserver
```

The API should then be available at:

```text
http://127.0.0.1:8000/
```

The Django admin panel is available at:

```text
http://127.0.0.1:8000/admin/
```

---

# Example Authentication Flow

A basic development test can be performed with Postman.

### 1. Register

```http
POST /auth/register/request-otp
```

```json
{
    "phone_number": "+905XXXXXXXXX"
}
```

The development server returns the OTP.

### 2. Verify registration

```http
POST /auth/register/verify/
```

```json
{
    "phone_number": "+905XXXXXXXXX",
    "otp": "123456"
}
```

The response contains:

```json
{
    "access": "...",
    "refresh": "..."
}
```

### 3. Copy the access token

Use:

```http
Authorization: JWT <access_token>
```

for authenticated endpoints.

### 4. Test the profile endpoint

Send the JWT with:

```http
GET /users/me/about/
```

### 5. Login again later

```http
POST /auth/login/request-otp/
```

Then:

```http
POST /auth/login/verify/
```

to receive a new JWT pair.

---

# Planned Features

The following features are planned but are **not necessarily complete yet**.

## Real OTP delivery

Replace development OTP responses with an actual SMS provider.

```text
API
 ↓
OTP generation
 ↓
SMS provider
 ↓
User's phone
```

---

## OTP request rate limiting

The current OTP system limits verification attempts, but production authentication should also include proper rate limiting for **OTP requests themselves**.

Planned protections include:

- Maximum OTP requests within a time window
- IP-based throttling
- Phone-number-based throttling
- Protection against automated request flooding
- Server-side throttling rather than relying on frontend restrictions

The frontend can prevent accidental/repeated requests, but it must **never be considered the security boundary**.

---

## Refresh-token rotation and revocation

The project needs stronger token lifecycle management.

In particular, when security-sensitive account information changes, such as changing the phone number or password, previously issued tokens should be invalidated where appropriate.

Planned work includes:

- Refresh-token rotation
- Token revocation/blacklisting
- Token-version invalidation
- Better session management
- Logout/session invalidation

---

## User search

Users should be discoverable using:

- Username
- Phone number when appropriate/available

Username lookup should be case-insensitive.

For example:

```text
@Amir
@amir
@AmIr
```

should identify the same account.

Privacy rules for phone-number searching still need to be finalized.

---

# Messaging System

The database structure is designed around:

```text
Conversation
ConversationMember
Message
Attachment
```

Messages are associated with a conversation and a sender.

The planned message functionality includes:

- Sending messages
- Retrieving message history
- Editing messages
- Soft-deleting messages
- Attachments
- Message timestamps
- Sender information
- Conversation membership authorization

---

# Real-Time Messaging

Django Channels/WebSockets are included/planned for real-time communication.

The eventual architecture is intended to allow:

```text
Client
  │
  │ WebSocket
  ▼
Django Channels
  │
  ▼
Conversation
  │
  ├── User A
  ├── User B
  └── User C
```

This will allow messages to appear without repeatedly polling the REST API.

---

# Frontend

The backend is being developed separately from the final client.

The eventual application should support a proper chat interface with:

- Conversation list
- Private chats
- Group chats
- Message history
- Real-time messages
- User profiles
- Profile pictures
- Online status
- Typing indicators
- Message editing/deletion
- Attachments

A web frontend can be built first, while the backend API can later be consumed by a mobile application as well.

---

# Security Considerations

Security is an important part of this project.

Current/implemented security-related concepts include:

- JWT authentication
- Authentication permissions
- Conversation membership permissions
- OTP hashing
- OTP expiration
- OTP attempt limits
- Temporary OTP lockouts
- Django password hashing
- Django password validators
- User authorization through `request.user`
- Queryset-based access control

Planned security improvements include:

- Production SMS delivery
- API throttling
- Token revocation
- Refresh-token rotation
- Better session management
- More comprehensive automated security tests
- Production deployment security
- HTTPS
- Secure cookie/header configuration where applicable
- Improved privacy controls around user discovery

---

# Testing

The project contains test infrastructure.

Run the test suite with:

```bash
pytest
```

As the project grows, tests should cover:

- Registration
- Login
- OTP expiration
- Invalid OTPs
- OTP lockouts
- Repeated OTP requests
- Password verification
- Username uniqueness
- Case-insensitive username lookup
- Conversation permissions
- Conversation membership
- Group administration
- Message permissions
- Token invalidation
- Phone-number changes

---

# Project Status

Chatty is a **learning/development project**.

The authentication foundation, custom user system, OTP workflow, JWT authentication, profile management, and the initial conversation architecture are being built first.

The messaging layer, real-time communication, production OTP delivery, stronger token/session management, frontend, and mobile support are still part of the ongoing development roadmap.

The architecture will likely change as new requirements and security considerations are discovered during development.
