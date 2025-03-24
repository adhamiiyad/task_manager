from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from flask import url_for

db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    
    def __repr__(self):
        return f'<Role {self.name}>'

project_members = db.Table('project_members',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), nullable=False, default=2),
    db.Column('status', db.String(20), nullable=False, default='active')
)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # friend_request, project_invite, etc.
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('notifications', lazy='dynamic'))

    def get_link(self):
        """Get the appropriate link based on notification type"""
        if self.type in ['friend_request', 'friend_request_accepted']:
            return url_for('users.profile')
        return None

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # User profile
    profile_picture = db.Column(db.BLOB)
    full_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    contact_info = db.Column(db.String(150))
    
    # Relationships
    owned_projects = db.relationship('Project', backref='owner', lazy='dynamic')
    assigned_tasks = db.relationship('Task', backref='assignee', lazy='dynamic')
    join_requests = db.relationship('ProjectRequest', backref='requester', lazy='dynamic')
    dashboard_items = db.relationship('DashboardItem', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    dashboard_stats = db.relationship('DashboardStat', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    # Friends relationship
    sent_friend_requests = db.relationship('Friendship',
                                          foreign_keys='Friendship.user_id',
                                          backref='sender',
                                          lazy='dynamic')
    received_friend_requests = db.relationship('Friendship',
                                             foreign_keys='Friendship.friend_id',
                                             backref='receiver',
                                             lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_friends(self):
        sent = Friendship.query.filter_by(user_id=self.id, status='accepted').all()
        received = Friendship.query.filter_by(friend_id=self.id, status='accepted').all()
        
        friends = []
        for friendship in sent:
            friends.append(User.query.get(friendship.friend_id))
        for friendship in received:
            friends.append(User.query.get(friendship.user_id))
            
        return friends
    
    def get_unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()
    
    def send_friend_request(self, friend):
        if friend.id == self.id:
            return False, "You cannot send a friend request to yourself"
            
        existing = Friendship.query.filter(
            ((Friendship.user_id == self.id) & (Friendship.friend_id == friend.id)) |
            ((Friendship.user_id == friend.id) & (Friendship.friend_id == self.id))
        ).first()
        
        if existing:
            if existing.status == 'accepted':
                return False, "You are already friends"
            elif existing.status == 'pending':
                return False, "A friend request already exists"
            
        friendship = Friendship(user_id=self.id, friend_id=friend.id)
        notification = Notification(
            user_id=friend.id,
            type='friend_request',
            message=f"{self.username} has sent you a friend request"
        )
        
        db.session.add(friendship)
        db.session.add(notification)
        db.session.commit()
        return True, "Friend request sent successfully"
    
    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # Relationships
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    members = db.relationship('User', secondary=project_members, backref=db.backref('projects', lazy='dynamic'))
    join_requests = db.relationship('ProjectRequest', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_member_role(self, user_id):
        # Query the project_members table to get the role
        member = db.session.execute(
            project_members.select()
            .where(project_members.c.project_id == self.id)
            .where(project_members.c.user_id == user_id)
        ).fetchone()
        
        if member:
            return Role.query.get(member.role_id)
        return None
    
    def __repr__(self):
        return f'<Project {self.title}>'

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='backlog')  # backlog, in_progress, completed
    priority = db.Column(db.String(20))  # low, medium, high
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # Foreign Keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    comments = db.relationship('Comment', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Task {self.title}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    parent = db.relationship('Comment', remote_side=[id], backref=db.backref('replies', lazy='dynamic'))
    likes = db.relationship('CommentLike', backref='comment', lazy='dynamic', cascade='all, delete-orphan')
    interactions = db.relationship('CommentInteraction', backref='comment', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_likes_count(self):
        return self.likes.count()
    
    def is_liked_by(self, user):
        return self.likes.filter_by(user_id=user.id).first() is not None
    
    def is_acknowledged_by(self, user):
        return self.interactions.filter_by(user_id=user.id, type='got_it').first() is not None

class CommentLike(db.Model):
    __tablename__ = 'comment_likes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # Ensure a user can only like a comment once
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', name='unique_comment_like'),)

class CommentInteraction(db.Model):
    __tablename__ = 'comment_interactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # e.g., 'got_it'
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref=db.backref('comment_interactions', lazy='dynamic'))
    
    # Ensure a user can only have one interaction of each type per comment
    __table_args__ = (db.UniqueConstraint('user_id', 'comment_id', 'type', name='unique_comment_interaction'),)

class Friendship(db.Model):
    __tablename__ = 'friendships'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    def __repr__(self):
        return f'<Friendship between {self.user_id} and {self.friend_id}>'

class ProjectRequest(db.Model):
    __tablename__ = 'project_requests'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    def __repr__(self):
        return f'<ProjectRequest by {self.user_id} for {self.project_id}>'

class DashboardItem(db.Model):
    __tablename__ = 'dashboard_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # project, task, chart
    item_id = db.Column(db.Integer)  # ID of the associated item
    position = db.Column(db.Integer)  # Position on dashboard
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    
    def __repr__(self):
        return f'<DashboardItem {self.item_type} for {self.user_id}>'

class DashboardStat(db.Model):
    __tablename__ = 'dashboard_stats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stat_date = db.Column(db.Date)
    tasks_completed = db.Column(db.Integer, default=0)
    tasks_created = db.Column(db.Integer, default=0)
    comments_added = db.Column(db.Integer, default=0)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'stat_date', name='unique_user_daily_stat'),)
    
    def __repr__(self):
        return f'<DashboardStat for {self.user_id} on {self.stat_date}>'