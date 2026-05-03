from flask import Blueprint, render_template, request, jsonify
from fpl_analysis import get_league_data, get_current_standings, get_expected_standings, get_predicted_standings
from medium import fetch_articles
import json

bp = Blueprint("main", __name__)


def load_projects():
    with open("projects.json") as f:
        return json.load(f)


@bp.route("/")
def index():
    articles = fetch_articles()
    return render_template("index.html", articles=articles)


@bp.route("/project/<slug>")
def project(slug):
    projects = load_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj:
        return "Project not found", 404
    return render_template("project.html", project=proj)


@bp.route("/projects/filter")
def filter_projects():
    tag = request.args.get("tag", "")
    projects = load_projects()
    if tag:
        projects = [p for p in projects if tag in p.get("tags", [])]
    return render_template("partials/project_cards.html", projects=projects)


@bp.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")
    print(f"Message from {name} ({email}): {message}")
    return render_template("partials/contact_success.html", name=name)


@bp.route("/api/chart/<slug>")
def chart_data(slug):
    projects = load_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj or "chart_data" not in proj:
        return jsonify({"error": "No chart data"}), 404
    return jsonify(proj["chart_data"])


@bp.route("/fpl")
def fpl():
    return render_template("fpl.html")


@bp.route("/fpl/analyse", methods=["POST"])
def fpl_analyse():
    league_id = request.form.get("league_id", "").strip()
    if not league_id:
        return render_template("fpl.html", error="Please enter a league ID.")
    try:
        n_sims = int(request.form.get("simulations", 1000))
        if n_sims not in (1000, 10000):
            n_sims = 1000
        league_data = get_league_data(league_id)
        league_name = league_data["league"]["name"]
        standings, scatter = get_current_standings(league_data)
        expected = get_expected_standings(league_data)
        monte_carlo, position_cols = get_predicted_standings(league_data, n_simulations=n_sims)
    except Exception as e:
        return render_template("fpl.html", error=f"Could not load league {league_id}: {e}")
    return render_template(
        "fpl_results.html",
        league_name=league_name,
        standings=standings,
        scatter=scatter,
        expected=expected,
        monte_carlo=monte_carlo,
        position_cols=position_cols,
    )
