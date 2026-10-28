
import os

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from models import db, WorkItem, PrioritySetting
from priority_engine import (
    CRITERIA,
    calculate_priority,
    explain_priority,
)
from dependency_engine import analyze_dependencies
from sprint_planner import plan_sprint
from risk_analyzer import analyze_sprint_risk


app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "backlogvision-local-development-key",
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///backlogvision.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


CRITERION_LABELS = {
    "business_value": "Business Value",
    "urgency": "Urgency",
    "customer_impact": "Customer Impact",
    "risk_reduction": "Risk Reduction",
    "strategic_alignment": "Strategic Alignment",
}


def get_weights():
    """Load priority weights saved in the database."""
    settings = PrioritySetting.query.all()
    weights = {
        setting.criterion: setting.weight
        for setting in settings
    }

    if set(weights) != set(CRITERIA):
        return None

    if any(
        not isinstance(weight, (int, float))
        or not 0 <= weight <= 100
        for weight in weights.values()
    ):
        return None

    if abs(sum(weights.values()) - 100) > 0.01:
        return None

    return weights


def weights_are_valid(weights):
    """Check that all five weights are valid and total 100%."""
    if set(weights.keys()) != set(CRITERIA):
        return False

    try:
        values = [float(weights[key]) for key in CRITERIA]
    except (TypeError, ValueError):
        return False

    return (
        all(0 <= value <= 100 for value in values)
        and abs(sum(values) - 100) <= 0.01
    )


def get_item_data(item, weights):
    """Convert a database item into data used by the priority engine."""
    data = {
        "id": item.id,
        "title": item.title,
        "description": item.description or "",
        "work_item_type": item.work_item_type,
        "state": item.state,
        "business_value": item.business_value,
        "urgency": item.urgency,
        "customer_impact": item.customer_impact,
        "risk_reduction": item.risk_reduction,
        "strategic_alignment": item.strategic_alignment,
        "effort": item.effort,
        "story_points": item.story_points,
        "depends_on": [
            dependency.id
            for dependency in item.prerequisites
        ],
    }

    if weights:
        priority = calculate_priority(data, weights)
        explanation = explain_priority(data, weights)

        data["priority_score"] = priority["score"]
        data["priority_explanation"] = explanation
    else:
        data["priority_score"] = None
        data["priority_explanation"] = None

    return data


def validate_dependencies(item_id, dependency_ids):
    """Reject missing dependencies and circular dependency links."""
    all_items = WorkItem.query.all()
    item_data = []

    for item in all_items:
        dependencies_for_item = [
            dependency.id
            for dependency in item.prerequisites
        ]

        if item.id == item_id:
            dependencies_for_item = dependency_ids

        item_data.append({
            "id": item.id,
            "title": item.title,
            "state": item.state,
            "depends_on": dependencies_for_item,
        })

    if item_id is not None and not any(
        item["id"] == item_id for item in item_data
    ):
        return False, "The selected work item does not exist."

    if item_id is None:
        temporary_id = (
            max((item["id"] for item in item_data), default=0) + 1
        )

        item_data.append({
            "id": temporary_id,
            "title": "New work item",
            "state": "New",
            "depends_on": dependency_ids,
        })

    try:
        analyze_dependencies(item_data)
    except ValueError as exc:
        return False, str(exc)

    return True, None


def parse_item_form(form):
    """Validate and parse fields submitted by add/edit forms."""
    text_fields = {
        "title": form.get("title", "").strip(),
        "description": form.get("description", "").strip(),
        "work_item_type": form.get(
            "work_item_type", "User Story"
        ).strip(),
        "state": form.get("state", "New").strip(),
    }

    if not text_fields["title"]:
        raise ValueError("Title is required.")

    if len(text_fields["title"]) > 200:
        raise ValueError("Title must be 200 characters or fewer.")

    if not text_fields["work_item_type"]:
        raise ValueError("Work item type is required.")

    if not text_fields["state"]:
        raise ValueError("State is required.")

    numeric_fields = (
        "business_value",
        "urgency",
        "customer_impact",
        "risk_reduction",
        "strategic_alignment",
        "effort",
        "story_points",
    )

    data = dict(text_fields)

    for field in numeric_fields:
        raw_value = form.get(field, "").strip()

        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            raise ValueError(
                f"{field.replace('_', ' ').title()} "
                "must be a whole number."
            )

        if field in CRITERIA:
            if not 1 <= value <= 10:
                raise ValueError(
                    f"{field.replace('_', ' ').title()} "
                    "must be between 1 and 10."
                )
        elif value <= 0:
            raise ValueError(
                f"{field.replace('_', ' ').title()} "
                "must be greater than zero."
            )

        data[field] = value

    # The add/edit templates use name="depends_on".
    raw_dependencies = form.getlist("depends_on")

    try:
        dependency_ids = sorted({
            int(value)
            for value in raw_dependencies
            if value
        })
    except (TypeError, ValueError):
        raise ValueError("Invalid dependency selection.")

    data["prerequisite_ids"] = dependency_ids

    return data


def save_item(item, data):
    """Save work item fields and dependency relationships."""
    item.title = data["title"]
    item.description = data["description"]
    item.work_item_type = data["work_item_type"]
    item.state = data["state"]
    item.business_value = data["business_value"]
    item.urgency = data["urgency"]
    item.customer_impact = data["customer_impact"]
    item.risk_reduction = data["risk_reduction"]
    item.strategic_alignment = data["strategic_alignment"]
    item.effort = data["effort"]
    item.story_points = data["story_points"]

    dependency_ids = data["prerequisite_ids"]

    if item.id is not None and item.id in dependency_ids:
        raise ValueError("A work item cannot depend on itself.")

    existing_items = (
        {
            work_item.id: work_item
            for work_item in WorkItem.query.filter(
                WorkItem.id.in_(dependency_ids)
            ).all()
        }
        if dependency_ids
        else {}
    )

    missing_ids = set(dependency_ids) - set(existing_items)

    if missing_ids:
        raise ValueError(
            "One or more selected dependencies do not exist."
        )

    item.prerequisites = [
        existing_items[dependency_id]
        for dependency_id in dependency_ids
    ]


@app.route("/")
def index():
    weights = get_weights()
    database_items = WorkItem.query.order_by(
        WorkItem.id.desc()
    ).all()

    items = []

    for item in database_items:
        data = get_item_data(item, weights)
        data["prerequisites"] = item.prerequisites
        items.append(data)

    if weights:
        items.sort(
            key=lambda item: (
                -(item["priority_score"] or 0),
                item["id"],
            )
        )

    return render_template(
        "index.html",
        items=items,
        weights=weights,
        criteria=CRITERIA,
        labels=CRITERION_LABELS,
    )


@app.route("/add", methods=["GET", "POST"])
def add_story():
    all_items = WorkItem.query.order_by(
        WorkItem.id.asc()
    ).all()

    selected_dependencies = []

    if request.method == "POST":
        selected_dependencies = [
            int(value)
            for value in request.form.getlist("depends_on")
            if value.isdigit()
        ]

        try:
            data = parse_item_form(request.form)

            valid, error = validate_dependencies(
                None,
                data["prerequisite_ids"],
            )

            if not valid:
                raise ValueError(error)

            item = WorkItem()
            save_item(item, data)

            db.session.add(item)
            db.session.commit()

            flash("Work item added successfully.", "success")
            return redirect(url_for("index"))

        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template(
        "add_story.html",
        items=all_items,
        available_items=all_items,
        selected_dependencies=selected_dependencies,
    )


@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_story(item_id):
    item = db.get_or_404(WorkItem, item_id)

    all_items = WorkItem.query.filter(
        WorkItem.id != item_id
    ).order_by(WorkItem.id.asc()).all()

    selected_dependencies = [
        dependency.id
        for dependency in item.prerequisites
    ]

    if request.method == "POST":
        selected_dependencies = [
            int(value)
            for value in request.form.getlist("depends_on")
            if value.isdigit()
        ]

        try:
            data = parse_item_form(request.form)

            valid, error = validate_dependencies(
                item_id,
                data["prerequisite_ids"],
            )

            if not valid:
                raise ValueError(error)

            save_item(item, data)
            db.session.commit()

            flash("Work item updated successfully.", "success")
            return redirect(url_for("index"))

        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")

    return render_template(
        "edit_story.html",
        item=item,
        items=all_items,
        available_items=all_items,
        selected_dependencies=selected_dependencies,
    )


@app.route("/delete/<int:item_id>", methods=["POST"])
def delete_story(item_id):
    item = db.get_or_404(WorkItem, item_id)

    try:
        item.prerequisites = []
        item.dependents = []

        db.session.delete(item)
        db.session.commit()

        flash("Work item deleted successfully.", "success")

    except Exception:
        db.session.rollback()
        app.logger.exception("Unable to delete work item.")
        flash("Could not delete the work item.", "error")

    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            weights = {}

            for criterion in CRITERIA:
                raw_value = request.form.get(
                    criterion, ""
                ).strip()

                try:
                    weights[criterion] = float(raw_value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Enter a valid weight for "
                        f"{CRITERION_LABELS[criterion]}."
                    )

            if not weights_are_valid(weights):
                raise ValueError(
                    "Weights must be between 0 and 100 "
                    "and total exactly 100%."
                )

            for criterion in CRITERIA:
                setting = PrioritySetting.query.filter_by(
                    criterion=criterion
                ).first()

                if setting is None:
                    setting = PrioritySetting(
                        criterion=criterion
                    )
                    db.session.add(setting)

                setting.weight = weights[criterion]

            db.session.commit()

            flash(
                "Priority settings saved successfully.",
                "success",
            )
            return redirect(url_for("settings"))

        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")

    saved_settings = {
        setting.criterion: setting.weight
        for setting in PrioritySetting.query.all()
    }

    return render_template(
        "settings.html",
        weights=saved_settings,
        criteria=CRITERIA,
        labels=CRITERION_LABELS,
    )


@app.route("/sprint", methods=["GET", "POST"])
def sprint():
    weights = get_weights()

    if not weights:
        flash(
            "Configure all five priority weights to total 100% "
            "before creating a sprint plan.",
            "error",
        )
        return redirect(url_for("settings"))

    database_items = WorkItem.query.order_by(
        WorkItem.id.asc()
    ).all()

    items = [
        get_item_data(item, weights)
        for item in database_items
    ]

    dependency_data = [
        {
            "id": item["id"],
            "title": item["title"],
            "state": item["state"],
            "depends_on": item["depends_on"],
        }
        for item in items
    ]

    try:
        dependency_results = analyze_dependencies(
            dependency_data
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))

    for item in items:
        dependency_info = dependency_results[item["id"]]
        item["blocked"] = dependency_info["blocked"]
        item["blocked_by"] = dependency_info["blocked_by"]

    sprint_result = None
    sprint_risk = None

    if request.method == "POST":
        try:
            capacity = int(
                request.form.get("capacity", "")
            )

            sprint_result = plan_sprint(items, capacity)

            selected_ids = {
                item["id"]
                for item in sprint_result["stories"]
            }

            selected_items = [
                item
                for item in items
                if item["id"] in selected_ids
            ]

            sprint_risk = analyze_sprint_risk(
                selected_items,
                capacity,
            )

        except (ValueError, TypeError) as exc:
            flash(
                str(exc) or "Enter a valid sprint capacity.",
                "error",
            )

    return render_template(
        "sprint.html",
        items=items,
        sprint_result=sprint_result,
        sprint_risk=sprint_risk,
        weights=weights,
        labels=CRITERION_LABELS,
    )


# Create the database tables if they do not already exist.
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    # Required for access through Docker's published port.
    # Disable debug mode and the reloader so the container's
    # main process stays running.
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        use_reloader=False,
    )
