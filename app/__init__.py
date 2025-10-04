from flask import Flask
from app.routes import auth, core, edit_async, upload
from app.config import Config
from app import extensions
from app.security import load_user

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    extensions.init_app(app)

    extensions.login_manager.user_loader(load_user)

    app.register_blueprint(auth.bp)
    app.register_blueprint(core.bp)
    app.register_blueprint(edit_async.bp)
    app.register_blueprint(upload.bp)

    return app
