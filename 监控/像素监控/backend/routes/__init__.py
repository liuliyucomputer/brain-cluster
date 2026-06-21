"""Register all blueprints"""

from flask import Flask

from .agents import bp as agents_bp
from .commander import bp as commander_bp
from .events import bp as events_bp
from .eyes import bp as eyes_bp
from .join_leave import bp as join_leave_bp
from .logs import bp as logs_bp
from .memo import bp as memo_bp
from .memory import bp as memory_bp
from .monitor import bp as monitor_bp
from .services import bp as services_bp
from .state import bp as state_bp
from .tasks import bp as tasks_bp
from .views import bp as views_bp


def register_blueprints(app: Flask):
    app.register_blueprint(agents_bp)
    app.register_blueprint(commander_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(eyes_bp)
    app.register_blueprint(join_leave_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(memo_bp)
    app.register_blueprint(memory_bp)
    app.register_blueprint(monitor_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(state_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(views_bp)
