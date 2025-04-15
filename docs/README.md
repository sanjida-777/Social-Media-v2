# Social Media Application Documentation

This directory contains the documentation for the Social Media Application.

## Documentation Structure

- **Project Overview**: General information about the project (cross-view of main README)
- **API Reference**: Details about the application's API endpoints
- **User Guide**: Instructions for end users
- **Developer Guide**: Information for developers working on the project
- **Architecture**: System architecture and design decisions
- **Database Schema**: Database structure and relationships

## Available Documentation

- [Project Overview](project_overview.md) - General information about the project
- [User Guide](user_guide.md) - Step-by-step instructions for using the application
- [API Reference](api.md) - Details about the application's API endpoints
- [System Architecture](architecture.md) - Information about the system design
- [Database Schema](database_schema.md) - Documentation of the database structure

## Building the Documentation

The documentation is built using [Sphinx](https://www.sphinx-doc.org/), a powerful documentation generator.

### Prerequisites

- Python 3.8+
- Sphinx

### Installation

1. Install Sphinx and required extensions:
   ```
   pip install sphinx sphinx-rtd-theme
   ```

2. Build the documentation:
   ```
   cd docs
   make html
   ```

3. View the documentation:
   Open `_build/html/index.html` in your web browser

## Contributing to Documentation

1. Documentation is written in reStructuredText (`.rst`) or Markdown (`.md`) format
2. Place new documentation files in the appropriate directory
3. Update the table of contents in `index.rst` when adding new files
4. Build and test the documentation locally before submitting changes

## Documentation Style Guide

- Use clear, concise language
- Include code examples where appropriate
- Use proper headings and structure
- Include screenshots for UI-related documentation
- Link to related documentation sections when relevant

## API Documentation

API endpoints are documented using OpenAPI/Swagger. The API specification can be found in the `api/` directory.

## Database Schema Documentation

Database schema documentation includes entity-relationship diagrams and detailed descriptions of tables and relationships.

## User Guide

The user guide provides step-by-step instructions for using the application, including account creation, profile management, posting content, and interacting with other users.
