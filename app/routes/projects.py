from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.models import db, Project, User, ProjectRequest, project_members, Role
bp = Blueprint("projects", __name__, url_prefix="/projects")


@bp.route("/")
@login_required
def list_projects():
    owned_projects = current_user.owned_projects.all()
    member_projects = current_user.projects.all()
    return render_template(
        "projects/list.html",
        owned_projects=owned_projects,
        member_projects=member_projects,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
def create_project():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")

        if not title:
            flash("Project title is required.")
            return redirect(url_for("projects.create_project"))

        new_project = Project(
            title=title, description=description, owner_id=current_user.id
        )
        new_project.members.append(current_user)

        db.session.add(new_project)
        db.session.commit()

        flash("Project created successfully!")
        return redirect(url_for("projects.view_project", project_id=new_project.id))

    return render_template("projects/create.html")


@bp.route("/<int:project_id>")
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id and current_user not in project.members:
        flash("You do not have access to this project.")
        return redirect(url_for("projects.list_projects"))

    tasks = project.tasks.all()
    members = project.members
    
    # Get members with their roles
    members_with_roles = []
    for member in members:
        role_info = db.session.execute(
            db.select(Role)
            .join(project_members, Role.id == project_members.c.role_id)
            .where(project_members.c.project_id == project_id)
            .where(project_members.c.user_id == member.id)
        ).fetchone()
        
        role = role_info[0] if role_info else None
        members_with_roles.append({
            'user': member,
            'role': role
        })

    return render_template(
        "projects/view.html", 
        project=project, 
        tasks=tasks, 
        members_with_roles=members_with_roles
    )


@bp.route("/<int:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Only the project owner can edit project details.")
        return redirect(url_for("projects.view_project", project_id=project.id))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")

        if not title:
            flash("Project title is required.")
            return redirect(url_for("projects.edit_project", project_id=project.id))

        project.title = title
        project.description = description
        db.session.commit()

        flash("Project updated successfully!")
        return redirect(url_for("projects.view_project", project_id=project.id))

    return render_template("projects/edit.html", project=project)


@bp.route("/<int:project_id>/members", methods=["GET", "POST"])
@login_required
def manage_members(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Only the project owner can manage members.")
        return redirect(url_for("projects.view_project", project_id=project.id))

    if request.method == "POST":
        username = request.form.get("username")
        role_id = request.form.get("role_id", "2")  # Default to member role (assuming ID 2 is member)
        
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                if user in project.members:
                    flash(f"{username} is already a member of this project.")
                else:
                    # First check if role ID is valid
                    role = Role.query.get(role_id)
                    if not role:
                        flash("Invalid role selected.")
                        return redirect(url_for("projects.manage_members", project_id=project.id))
                    
                    # Add user to members with the specified role
                    stmt = project_members.insert().values(
                        user_id=user.id,
                        project_id=project.id,
                        role_id=role_id,
                        status='active'
                    )
                    db.session.execute(stmt)
                    db.session.commit()
                    
                    flash(f"{username} added to the project with {role.name} role.")
            else:
                flash(f"User {username} not found.")
    
    # Get all roles for the dropdown
    roles = Role.query.all()
    
    # Get pending join requests
    pending_requests = ProjectRequest.query.filter_by(project_id=project_id, status="pending").all()
    
    # Get project members with their roles
    members_with_roles = []
    for member in project.members:
        role_info = db.session.execute(
            db.select(Role)
            .join(project_members, Role.id == project_members.c.role_id)
            .where(project_members.c.project_id == project_id)
            .where(project_members.c.user_id == member.id)
        ).fetchone()
        
        role = role_info[0] if role_info else None
        members_with_roles.append({
            'user': member,
            'role': role
        })
    
    return render_template(
        "projects/members.html", 
        project=project, 
        pending_requests=pending_requests,
        roles=roles,
        members_with_roles=members_with_roles
    )


@bp.route("/<int:project_id>/members/<int:user_id>/remove")
@login_required
def remove_member(project_id, user_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Only the project owner can remove members.")
        return redirect(url_for("projects.view_project", project_id=project.id))

    if project.owner_id == user_id:
        flash("Cannot remove the project owner.")
        return redirect(url_for("projects.manage_members", project_id=project.id))

    user = User.query.get_or_404(user_id)
    if user in project.members:
        project.members.remove(user)
        db.session.commit()
        flash(f"{user.username} removed from the project.")

    return redirect(url_for("projects.manage_members", project_id=project.id))


@bp.route("/<int:project_id>/members/<int:user_id>/update-role", methods=["POST"])
@login_required
def update_member_role(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    if project.owner_id != current_user.id:
        flash("Only the project owner can update member roles.")
        return redirect(url_for("projects.view_project", project_id=project.id))
    
    # Get the role ID
    role_id = request.form.get("role_id")
    if not role_id:
        flash("Role ID is required.")
        return redirect(url_for("projects.manage_members", project_id=project.id))
    
    # Make sure the role exists
    role = Role.query.get(role_id)
    if not role:
        flash("Invalid role selected.")
        return redirect(url_for("projects.manage_members", project_id=project.id))
    
    # Update the role directly in the association table
    stmt = project_members.update().where(
        project_members.c.project_id == project_id,
        project_members.c.user_id == user_id
    ).values(role_id=role_id)
    
    db.session.execute(stmt)
    db.session.commit()
    
    flash("Member role updated successfully.")
    return redirect(url_for("projects.manage_members", project_id=project.id))


@bp.route("/<int:project_id>/join-request", methods=["POST"])
@login_required
def request_to_join(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Check if user is already a member
    if current_user in project.members:
        flash("You are already a member of this project.")
        return redirect(url_for("projects.view_project", project_id=project.id))
    
    # Check if user already has a pending request
    existing_request = ProjectRequest.query.filter_by(
        project_id=project_id,
        user_id=current_user.id,
        status="pending"
    ).first()
    
    if existing_request:
        flash("You already have a pending request to join this project.")
        return redirect(url_for("projects.list_projects"))
    
    # Create new join request
    join_request = ProjectRequest(
        project_id=project_id,
        user_id=current_user.id,
        status="pending"
    )
    
    db.session.add(join_request)
    db.session.commit()
    
    flash("Join request sent successfully.")
    return redirect(url_for("projects.list_projects"))


@bp.route("/<int:project_id>/request/<int:request_id>/<string:action>")
@login_required
def handle_request(project_id, request_id, action):
    project = Project.query.get_or_404(project_id)
    
    # Check if current user is project owner
    if project.owner_id != current_user.id:
        flash("Only the project owner can manage join requests.")
        return redirect(url_for("projects.view_project", project_id=project.id))
    
    join_request = ProjectRequest.query.get_or_404(request_id)
    
    # Make sure the request belongs to this project
    if join_request.project_id != project.id:
        flash("Invalid request.")
        return redirect(url_for("projects.manage_members", project_id=project.id))
    
    user = User.query.get(join_request.user_id)
    if not user:
        flash("User not found.")
        return redirect(url_for("projects.manage_members", project_id=project.id))
    
    if action == "approve":
        # Get role ID from query param or form (default to member role - ID 2)
        role_id = request.args.get("role_id") or request.form.get("role_id", "2")
        
        # Check if role exists
        role = Role.query.get(role_id)
        if not role:
            flash("Invalid role selected.")
            return redirect(url_for("projects.manage_members", project_id=project.id))
        
        # Add user to project with specified role
        if user not in project.members:
            # Add to association table directly
            stmt = project_members.insert().values(
                user_id=user.id,
                project_id=project.id,
                role_id=role_id,
                status='active'
            )
            db.session.execute(stmt)
            
            # Update request status
            join_request.status = "approved"
            db.session.commit()
            flash(f"{user.username} has been added to the project with {role.name} role.")
        else:
            flash(f"{user.username} is already a member of this project.")
            
    elif action == "decline":
        join_request.status = "declined"
        db.session.commit()
        flash("Join request declined.")
    
    return redirect(url_for("projects.manage_members", project_id=project.id))


@bp.route("/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)

    if project.owner_id != current_user.id:
        flash("Only the project owner can delete the project.")
        return redirect(url_for("projects.view_project", project_id=project.id))

    db.session.delete(project)
    db.session.commit()

    flash("Project deleted successfully.")
    return redirect(url_for("projects.list_projects"))