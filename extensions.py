"""Application extensions module."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Flask-SQLAlchemy database instance shared across the project
# Additional extensions (e.g., cache, mail) can be added here later.
db = SQLAlchemy()
login_manager = LoginManager()
