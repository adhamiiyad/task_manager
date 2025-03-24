from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app.models.models import db, User, Project, Role, project_members, Friendship, Notification
from PIL import Image
import io

bp = Blueprint("users", __name__, url_prefix="/users")

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route("/profile")
@bp.route("/profile/<username>")
@login_required
def profile(username=None):
    if username:
        user = User.query.filter_by(username=username).first_or_404()
    else:
        user = current_user
    
    # Get user's projects with role information
    owned_projects = user.owned_projects.all()
    
    # Get member projects with role information
    member_projects = []
    for project in user.projects.all():
        if project.owner_id != user.id:  # Only include projects user is a member of, not owner
            role_info = db.session.execute(
                db.select(Role)
                .join(project_members, Role.id == project_members.c.role_id)
                .where(project_members.c.project_id == project.id)
                .where(project_members.c.user_id == user.id)
            ).fetchone()
            
            role = role_info[0] if role_info else None
            member_projects.append({
                'project': project,
                'role': role
            })
    
    # Get friend requests and friends only if viewing own profile
    friend_requests = user.received_friend_requests.filter_by(status='pending').all() if user == current_user else []
    friends = user.get_friends()
    
    # Check if current user can send friend request
    can_send_request = False
    if user != current_user:
        existing = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user.id)) |
            ((Friendship.user_id == user.id) & (Friendship.friend_id == current_user.id))
        ).first()
        can_send_request = not existing
    
    return render_template(
        "users/profile.html",
        user=user,
        owned_projects=owned_projects,
        member_projects=member_projects,
        friend_requests=friend_requests,
        friends=friends,
        can_send_request=can_send_request
    )

@bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        try:
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and allowed_file(file.filename):
                    # Read the image
                    image = Image.open(file)
                    
                    # Convert to RGB if necessary
                    if image.mode != 'RGB':
                        image = image.convert('RGB')
                    
                    # Resize image to 200x200 while maintaining aspect ratio
                    image.thumbnail((200, 200))
                    
                    # Convert to bytes
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='JPEG', quality=85)
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    current_user.profile_picture = img_byte_arr
            
            # Update other fields
            current_user.full_name = request.form.get('full_name')
            current_user.email = request.form.get('email')
            current_user.bio = request.form.get('bio')
            
            # Handle password change if provided
            new_password = request.form.get('new_password')
            if new_password:
                current_password = request.form.get('current_password')
                if current_user.check_password(current_password):
                    current_user.set_password(new_password)
                else:
                    flash('Current password is incorrect.', 'error')
                    return redirect(url_for('users.edit_profile'))
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('users.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile. Please try again.', 'error')
            return redirect(url_for('users.edit_profile'))
    
    return render_template("users/edit_profile.html")

@bp.route("/notifications")
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # Mark all as read
    unread = current_user.notifications.filter_by(is_read=False).all()
    for notification in unread:
        notification.is_read = True
    db.session.commit()
    
    return render_template("users/notifications.html", notifications=notifications)

@bp.route("/send_friend_request/<int:user_id>", methods=["POST"])
@login_required
def send_friend_request(user_id):
    user = User.query.get_or_404(user_id)
    success, message = current_user.send_friend_request(user)
    flash(message)
    return redirect(url_for('users.profile', username=user.username))

@bp.route("/handle_friend_request/<int:request_id>/<string:action>", methods=["POST"])
@login_required
def handle_friend_request(request_id, action):
    friend_request = Friendship.query.get_or_404(request_id)
    
    if friend_request.friend_id != current_user.id:
        abort(403)
    
    sender = User.query.get(friend_request.user_id)
    
    if action == 'accept':
        friend_request.status = 'accepted'
        notification = Notification(
            user_id=friend_request.user_id,
            type='friend_request_accepted',
            message=f"{current_user.username} has accepted your friend request"
        )
        db.session.add(notification)
        flash('Friend request accepted!')
    elif action == 'reject':
        friend_request.status = 'rejected'
        flash('Friend request rejected.')
    
    db.session.commit()
    return redirect(url_for('users.profile'))

@bp.route("/add_friend", methods=["POST"])
@login_required
def add_friend_by_username():
    username = request.form.get('username')
    if not username:
        flash('Please enter a username.', 'error')
        return redirect(url_for('users.profile'))
        
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('users.profile'))
        
    success, message = current_user.send_friend_request(user)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('users.profile'))

@bp.route("/remove_friend/<int:user_id>", methods=["GET"])
@login_required
def remove_friend(user_id):
    user = User.query.get_or_404(user_id)
    
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user.id)) |
        ((Friendship.user_id == user.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if friendship and friendship.status == 'accepted':
        notification = Notification(
            user_id=user.id,
            type='friend_removed',
            message=f"{current_user.username} has removed you from their friends list"
        )
        db.session.add(notification)
        
        db.session.delete(friendship)
        db.session.commit()
        
        flash('Friend removed successfully.', 'success')
    else:
        flash('Friend not found or already removed.', 'error')
    
    return redirect(url_for('users.profile')) 