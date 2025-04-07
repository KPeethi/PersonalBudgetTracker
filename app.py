import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

# Create a base class for declarative table definitions
class Base(DeclarativeBase):
    pass

# Create extensions without initializing them yet
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    # Create the Flask application
    app = Flask(__name__)
    
    # Configure application
    app.secret_key = os.environ.get("SESSION_SECRET", "expense-tracker-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'
    
    with app.app_context():
        # Import models here
        import models
        
        # Create all database tables
        db.create_all()
        
        # Setup user loader
        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))
    
    return app

# Create the application instance
app = create_app()