---
name: python-django
description: >-
  Django project structure, ORM patterns, views, templates, migrations.
  Use this skill when working on a Django project.
---

# Django Development

## Project Structure

```
myproject/
├── manage.py                 # CLI entry point
├── myproject/
│   ├── __init__.py
│   ├── settings.py           # Configuration
│   ├── urls.py               # Root URL conf
│   ├── wsgi.py / asgi.py     # Server entry points
├── myapp/
│   ├── models.py             # ORM models
│   ├── views.py              # View functions/classes
│   ├── urls.py               # App URL patterns
│   ├── serializers.py        # DRF serializers (if using REST framework)
│   ├── admin.py              # Admin registration
│   ├── tests.py              # Tests
│   └── migrations/           # Database migrations
```

## Key Patterns

### Models

```python
from django.db import models

class Resource(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
```

### Views (Class-Based)

```python
from django.views.generic import ListView, DetailView

class ResourceListView(ListView):
    model = Resource
    template_name = 'resources/list.html'
    paginate_by = 20
```

### Django REST Framework

```python
from rest_framework import viewsets, serializers

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'

class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
```

## Commands

```bash
python manage.py runserver           # Development server
python manage.py makemigrations      # Generate migrations
python manage.py migrate             # Apply migrations
python manage.py createsuperuser     # Create admin user
python manage.py shell               # Interactive shell
python manage.py test                # Run tests
python manage.py collectstatic       # Collect static files
```

## Guidelines

- Always create migrations after model changes
- Use `select_related()` and `prefetch_related()` to avoid N+1 queries
- Keep views thin — put business logic in model methods or services
- Use Django's built-in auth system for authentication
- Use `settings.py` for config; never hardcode secrets
- Use class-based views for CRUD; function views for simple logic
