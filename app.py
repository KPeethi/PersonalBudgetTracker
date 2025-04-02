import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "expense-tracker-secret-key")

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models here
    import models  # noqa: F401
    db.create_all()
    
    # Setup user loader
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))