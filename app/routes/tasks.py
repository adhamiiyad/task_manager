from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from datetime import datetime
from app.models.models import db, Task, Project, User, Comment, CommentLike, CommentInteraction

bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@bp.route("/create/<int:project_id>", methods=["GET", "POST"])
@login_required
def create_task(project_id):
    project = Project.query.get_or_404(project_id)

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this project.")
        return redirect(url_for("projects.list_projects"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date_str = request.form.get("due_date")
        priority = request.form.get("priority")
        assignee_id = request.form.get("assignee_id")

        if not title:
            flash("Task title is required.")
            return redirect(url_for("tasks.create_task", project_id=project.id))

        # Parse due date if provided
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.")
                return redirect(url_for("tasks.create_task", project_id=project.id))

        new_task = Task(
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            project_id=project.id,
            assignee_id=assignee_id if assignee_id else None,
            status="backlog",
        )

        db.session.add(new_task)
        db.session.commit()

        flash("Task created successfully!")
        return redirect(url_for("projects.view_project", project_id=project.id))

    # Get all project members for assignee selection
    members = project.members

    return render_template("tasks/create.html", project=project, members=members)


@bp.route("/<int:task_id>")
@login_required
def view_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this task.")
        return redirect(url_for("projects.list_projects"))

    comments = task.comments.order_by(Comment.created_at.asc()).all()

    return render_template(
        "tasks/view.html", task=task, project=project, comments=comments
    )


@bp.route("/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this task.")
        return redirect(url_for("projects.list_projects"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date_str = request.form.get("due_date")
        priority = request.form.get("priority")
        status = request.form.get("status")
        assignee_id = request.form.get("assignee_id")

        if not title:
            flash("Task title is required.")
            return redirect(url_for("tasks.edit_task", task_id=task.id))

        # Parse due date if provided
        if due_date_str:
            try:
                task.due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please use YYYY-MM-DD.")
                return redirect(url_for("tasks.edit_task", task_id=task.id))
        else:
            task.due_date = None

        task.title = title
        task.description = description
        task.priority = priority
        task.status = status
        task.assignee_id = assignee_id if assignee_id else None

        db.session.commit()

        flash("Task updated successfully!")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    # Get all project members for assignee selection
    members = project.members

    return render_template(
        "tasks/edit.html", task=task, project=project, members=members
    )


@bp.route("/<int:task_id>/status/<string:status>")
@login_required
def update_status(task_id, status):
    task = Task.query.get_or_404(task_id)
    project = task.project

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this task.")
        return redirect(url_for("projects.list_projects"))

    # Validate status
    valid_statuses = ["backlog", "in_progress", "completed"]
    if status not in valid_statuses:
        flash("Invalid status.")
        return redirect(url_for("tasks.view_task", task_id=task.id))

    task.status = status
    db.session.commit()

    flash("Task status updated.")
    return redirect(url_for("tasks.view_task", task_id=task.id))


@bp.route("/<int:task_id>/comment", methods=["POST"])
@login_required
def add_comment(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this task.")
        return redirect(url_for("projects.list_projects"))

    content = request.form.get("content")
    if content:
        comment = Comment(content=content, task_id=task.id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash("Comment added.")

    return redirect(url_for("tasks.view_task", task_id=task.id))


@bp.route("/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project

    # Check if user is owner or member of the project
    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this task.")
        return redirect(url_for("projects.list_projects"))

    project_id = task.project_id

    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully.")
    return redirect(url_for("projects.view_project", project_id=project_id))


@bp.route("/tasks/<int:task_id>/comments/<int:comment_id>/like", methods=["POST"])
@login_required
def toggle_comment_like(task_id, comment_id):
    task = Task.query.get_or_404(task_id)
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.task_id != task.id:
        abort(404)
    
    # Check if user already liked the comment
    existing_like = CommentLike.query.filter_by(
        user_id=current_user.id,
        comment_id=comment_id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        new_like = CommentLike(user_id=current_user.id, comment_id=comment_id)
        db.session.add(new_like)
    
    db.session.commit()
    return redirect(url_for('tasks.view_task', task_id=task_id))


@bp.route("/tasks/<int:task_id>/comments/<int:comment_id>/reply", methods=["POST"])
@login_required
def add_reply(task_id, comment_id):
    task = Task.query.get_or_404(task_id)
    parent_comment = Comment.query.get_or_404(comment_id)
    
    if parent_comment.task_id != task.id:
        abort(404)
    
    content = request.form.get('content')
    if not content:
        flash('Reply content cannot be empty.', 'error')
        return redirect(url_for('tasks.view_task', task_id=task_id))
    
    reply = Comment(
        content=content,
        user_id=current_user.id,
        task_id=task_id,
        parent_id=comment_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    flash('Reply added successfully!', 'success')
    return redirect(url_for('tasks.view_task', task_id=task_id))


@bp.route("/tasks/<int:task_id>/comments/<int:comment_id>/acknowledge", methods=["POST"])
@login_required
def toggle_comment_acknowledgment(task_id, comment_id):
    task = Task.query.get_or_404(task_id)
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.task_id != task.id:
        abort(404)
    
    # Check if user already acknowledged the comment
    existing_interaction = CommentInteraction.query.filter_by(
        user_id=current_user.id,
        comment_id=comment_id,
        type='got_it'
    ).first()
    
    if existing_interaction:
        db.session.delete(existing_interaction)
    else:
        new_interaction = CommentInteraction(
            user_id=current_user.id,
            comment_id=comment_id,
            type='got_it'
        )
        db.session.add(new_interaction)
    
    db.session.commit()
    return redirect(url_for('tasks.view_task', task_id=task_id))
