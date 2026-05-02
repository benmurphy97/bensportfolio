from flask import Flask, render_template, request, jsonify
from fpl_analysis import get_league_data, get_current_standings, get_expected_standings, get_predicted_standings
import json
import os

app = Flask(__name__)

# Load projects from JSON
def load_projects():
    with open("projects.json") as f:
        return json.load(f)

@app.route("/")
def index():
    projects = load_projects()
    tags = sorted(set(tag for p in projects for tag in p.get("tags", [])))
    return render_template("index.html", projects=projects, tags=tags)

@app.route("/project/<slug>")
def project(slug):
    projects = load_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj:
        return "Project not found", 404
    return render_template("project.html", project=proj)

# HTMX: filter projects by tag
@app.route("/projects/filter")
def filter_projects():
    tag = request.args.get("tag", "")
    projects = load_projects()
    if tag:
        projects = [p for p in projects if tag in p.get("tags", [])]
    return render_template("partials/project_cards.html", projects=projects)

# HTMX: handle contact form submission
@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")
    # TODO: send email / store message
    print(f"Message from {name} ({email}): {message}")
    return render_template("partials/contact_success.html", name=name)

# API: return chart data for a project
@app.route("/api/chart/<slug>")
def chart_data(slug):
    projects = load_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj or "chart_data" not in proj:
        return jsonify({"error": "No chart data"}), 404
    return jsonify(proj["chart_data"])


# FPL Draft Insights
@app.route("/fpl")
def fpl():
    return render_template("fpl.html")

@app.route("/fpl/analyse", methods=["POST"])
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


if __name__ == "__main__":
    app.run(debug=True)
