from flask import Blueprint, render_template

bp = Blueprint("views", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/obligations")
def obligations():
    return render_template("obligations.html")
