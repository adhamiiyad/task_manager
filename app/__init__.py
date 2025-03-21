from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from app.config import Config
import base64

from app.models.models import db, User, Notification


login_manager = LoginManager()
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Add custom filter for base64 encoding
    @app.template_filter('b64encode')
    def b64encode_filter(s):
        if s is None:
            return None
        return base64.b64encode(s).decode('utf-8')

    # Add template context processor
    @app.context_processor
    def utility_processor():
        return {'Notification': Notification}

    with app.app_context():
        # Import routes
        from app.routes import main, auth, projects, tasks, users

        # Register blueprints
        app.register_blueprint(main.bp)
        app.register_blueprint(auth.bp)
        app.register_blueprint(projects.bp)
        app.register_blueprint(tasks.bp)
        app.register_blueprint(users.bp)

        # Create database tables
        db.create_all()

    return app
