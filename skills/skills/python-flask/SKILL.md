---
name: python-flask
description: >-
  Flask application patterns, blueprints, extensions.
  Use this skill when working on a Flask project.
---

# Flask Development

## Project Structure

```
src/
├── app.py / __init__.py      # App factory
├── config.py                 # Configuration classes
├── routes/                   # Blueprint modules
│   ├── __init__.py
│   └── resources.py
├── models/                   # SQLAlchemy models
├── services/                 # Business logic
└── templates/                # Jinja2 templates (if serving HTML)
```

## Key Patterns

### App Factory

```python
from flask import Flask

def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or "config.Config")

    from routes.resources import bp as resources_bp
    app.register_blueprint(resources_bp, url_prefix="/api/v1")

    return app
```

### Blueprints

```python
from flask import Blueprint, jsonify, request

bp = Blueprint("resources", __name__)

@bp.route("/resources", methods=["GET"])
def list_resources():
    return jsonify({"items": []})

@bp.route("/resources", methods=["POST"])
def create_resource():
    data = request.get_json()
    return jsonify(data), 201
```

### Error Handling

```python
@app.errorhandler(404)
def not_found(e):
    return jsonify(error="Not found"), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify(error="Internal server error"), 500
```

## Commands

```bash
flask run                    # Development server
flask run --debug            # With auto-reload
flask shell                  # Interactive shell
flask db migrate             # Flask-Migrate: generate migration
flask db upgrade             # Flask-Migrate: apply migration
```

## Guidelines

- Use the app factory pattern for testability
- Organize routes with Blueprints
- Use Flask extensions: Flask-SQLAlchemy, Flask-Migrate, Flask-Login
- Use `request.get_json()` for JSON payloads
- Return tuples `(response, status_code)` for explicit status
- Use `current_app` for accessing app within request context
