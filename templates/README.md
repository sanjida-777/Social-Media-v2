# Template Organization

This directory contains all the templates for the SocialConnect application. The templates are organized into the following categories:

## Directory Structure

- **auth/** - Authentication-related templates
  - login.html - User login page
  - register.html - User registration page
  - forgot_password.html - Password recovery page
  - settings.html - User account settings

- **profile/** - User profile templates
  - profile.html - User profile page
  - edit_profile.html - Edit profile page

- **feed/** - News feed templates
  - index.html - Main feed page

- **post/** - Post-related templates
  - create_post.html - Create new post page

- **story/** - Story-related templates
  - story.html - View story page
  - create_story.html - Create new story page

- **friends/** - Friend-related templates
  - friends.html - Friends list and friend requests

- **messaging/** - Messaging templates
  - messages.html - Messages overview
  - inbox.html - Message inbox
  - chat.html - Chat interface
  - chat_group.html - Group chat interface

- **layout/** - Layout templates
  - base.html - Base template with common layout elements

- **test/** - Test templates
  - api_test.html - API testing page
  - test_filters.html - Template filter tests
  - upload_test.html - File upload testing

## Template Inheritance

All templates extend the base layout template (`layout/base.html`), which provides:

1. Common HTML structure
2. Navigation bars (top and mobile)
3. Footer
4. Common JavaScript and CSS includes
5. Flash message handling

## Usage

When creating a new template, place it in the appropriate category directory and extend the base template:

```jinja
{% extends "layout/base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
  <!-- Your content here -->
{% endblock %}
```

## Notes

- The `chat/` directory contains specialized chat templates
- The `main/` directory contains legacy templates that are being migrated to the new structure
