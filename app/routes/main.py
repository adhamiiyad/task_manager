from flask import Blueprint, render_template
from flask_login import login_required

from app.models.models import Project

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", Project=Project)
