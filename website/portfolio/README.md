# Portfolio App

A clean, minimal personal portfolio built with Flask + HTMX + Plotly.

## Stack
- **Flask** — routing, templating, API endpoints
- **Jinja2** — server-side HTML rendering
- **HTMX** — dynamic filtering and form submission without writing JS
- **Plotly.js** — interactive data visualisations
- **DM Serif Display / DM Sans / DM Mono** — typography

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5000`

## Project Structure

```
portfolio/
├── app.py                        # Flask app & routes
├── projects.json                 # Your project data
├── requirements.txt
├── templates/
│   ├── base.html                 # Shared layout
│   ├── index.html                # Home page (hero + projects + contact)
│   ├── project.html              # Project detail page
│   └── partials/
│       ├── project_cards.html    # Cards grid (used by HTMX filter too)
│       └── contact_success.html  # Contact form success message
└── static/
    ├── css/style.css
    └── js/main.js
```

## Adding a Project

Add an entry to `projects.json`:

```json
{
  "slug": "my-project",           // URL slug
  "title": "My Project",
  "summary": "One-line summary shown on the card",
  "description": "Full description on the detail page",
  "tags": ["Python", "ML"],
  "github": "https://github.com/...",
  "live": "",
  "chart_data": {                 // Optional — drives the Plotly chart
    "type": "bar",                // "bar", "line", or "scatter"
    "labels": ["A", "B", "C"],
    "values": [10, 20, 15]
  }
}
```

## Chart Types

Three chart types are supported out of the box in `project.html`:
- `"line"` — actual vs predicted (time series)
- `"bar"` — category bar chart
- `"scatter"` — cluster scatter plot

Extend the `<script>` block in `project.html` to add more Plotly chart types.
