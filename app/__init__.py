import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap # <--- ADD THIS LINE
from config import Config

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'main.login'

bootstrap = Bootstrap() # <--- ADD THIS LINE

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)
    bootstrap.init_app(app) # <--- ADD THIS LINE

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)

    from app.models import User

    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    with app.app_context():
        db.create_all()

    return app