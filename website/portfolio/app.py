from flask import Flask, render_template, request, jsonify
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

if __name__ == "__main__":
    app.run(debug=True)
