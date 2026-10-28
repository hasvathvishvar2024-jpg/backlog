
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Stores relationships between backlog items
dependencies = db.Table(
    "dependencies",
    db.Column(
        "story_id",
        db.Integer,
        db.ForeignKey("work_item.id"),
        primary_key=True
    ),
    db.Column(
        "dependency_id",
        db.Integer,
        db.ForeignKey("work_item.id"),
        primary_key=True
    )
)


class WorkItem(db.Model):
    __tablename__ = "work_item"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    work_item_type = db.Column(
        db.String(50), nullable=False, default="User Story"
    )

    state = db.Column(
        db.String(30), nullable=False, default="New"
    )

    # User-entered ratings from 1 to 10
    business_value = db.Column(db.Integer, nullable=False)
    urgency = db.Column(db.Integer, nullable=False)
    customer_impact = db.Column(db.Integer, nullable=False)
    risk_reduction = db.Column(db.Integer, nullable=False)
    strategic_alignment = db.Column(db.Integer, nullable=False)

    # Planning estimates
    effort = db.Column(db.Integer, nullable=False)
    story_points = db.Column(db.Integer, nullable=False)

    # Items this work item depends on
    prerequisites = db.relationship(
        "WorkItem",
        secondary=dependencies,
        primaryjoin=(id == dependencies.c.story_id),
        secondaryjoin=(id == dependencies.c.dependency_id),
        backref="dependents"
    )


class PrioritySetting(db.Model):
    __tablename__ = "priority_setting"

    id = db.Column(db.Integer, primary_key=True)

    criterion = db.Column(
        db.String(50), unique=True, nullable=False
    )

    # User-configured percentage weight
    weight = db.Column(db.Float, nullable=False)
