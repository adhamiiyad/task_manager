# Task Manager

A modern, feature-rich task management application built with Flask and Bootstrap, designed to help teams collaborate efficiently on projects.

## Features

### User Management
- **User Authentication**: Secure login and registration system
- **Profile Management**: 
  - Customizable user profiles with profile pictures
  - Bio and contact information
  - Password management
- **Friend System**:
  - Send and receive friend requests
  - Accept or reject friend requests
  - View friends list and their profiles

### Project Management
- **Project Creation and Organization**:
  - Create and manage multiple projects
  - Add project descriptions and details
  - Invite team members to projects
- **Role-based Access Control**:
  - Assign different roles to project members
  - Control access and permissions based on roles
- **Project Dashboard**:
  - Overview of project status
  - Recent activity tracking
  - Project statistics

### Task Management
- **Task Organization**:
  - Create, edit, and delete tasks
  - Set task priorities (low, medium, high)
  - Track task status (backlog, in progress, completed)
  - Set due dates
- **Task Assignment**:
  - Assign tasks to team members
  - Track task ownership
  - Monitor task progress
- **Comments and Collaboration**:
  - Comment on tasks
  - Like and acknowledge comments
  - Reply to comments
  - Nested comment threads

### Notifications
- Real-time notifications for:
  - Friend requests
  - Request acceptances
  - Project invitations
  - Task assignments
  - Comment mentions
- Mark notifications as read
- Notification history

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLAlchemy ORM
- **Frontend**: 
  - Bootstrap 5
  - Jinja2 Templates
  - Custom CSS
- **Authentication**: Flask-Login
- **Image Processing**: Pillow (PIL)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd task_manager
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export FLASK_APP=app
export FLASK_ENV=development
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Project Structure

```
task_manager/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   └── models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── main.py
│   │   ├── projects.py
│   │   ├── tasks.py
│   │   └── users.py
│   ├── static/css
│   │   └── style.css
│   └── templates/
│       ├── auth/
│       ├── projects/
│       ├── tasks/
│       └── users/
├── instance/
│   └── app.db
├── run.py
├── requirements.txt
└── README.md
```

## API Endpoints

### Authentication
```
POST /auth/login              # User login
POST /auth/register           # User registration
POST /auth/logout            # User logout
GET  /auth/reset-password    # Request password reset
POST /auth/reset-password    # Process password reset
```

### User Management
```
GET    /users/profile                    # Get current user's profile
GET    /users/profile/<username>         # Get specific user's profile
GET    /users/notifications              # Get user notifications
POST   /users/profile/edit               # Update user profile
POST   /users/send_friend_request/<id>   # Send friend request
POST   /users/handle_friend_request/<id> # Accept/reject friend request
POST   /users/add_friend                 # Add friend by username
```

### Project Management
```
GET    /projects                      # List all accessible projects
GET    /projects/<id>                 # Get project details
POST   /projects/create               # Create new project
PUT    /projects/<id>/edit           # Update project details
DELETE /projects/<id>                 # Delete project
POST   /projects/<id>/members/add    # Add member to project
DELETE /projects/<id>/members/<uid>  # Remove member from project
PUT    /projects/<id>/roles/<uid>    # Update member role
```

### Task Management
```
GET    /tasks                    # List all tasks (with filters)
GET    /tasks/<id>              # Get task details
POST   /projects/<id>/tasks     # Create new task in project
PUT    /tasks/<id>              # Update task details
DELETE /tasks/<id>              # Delete task
PUT    /tasks/<id>/status      # Update task status
PUT    /tasks/<id>/assign      # Assign task to user
```

### Comments and Interactions
```
GET    /tasks/<id>/comments           # Get task comments
POST   /tasks/<id>/comments           # Add comment to task
PUT    /comments/<id>                 # Edit comment
DELETE /comments/<id>                 # Delete comment
POST   /comments/<id>/reply           # Reply to comment
POST   /comments/<id>/like            # Toggle comment like
POST   /comments/<id>/acknowledge     # Toggle comment acknowledgment
```

### Dashboard and Statistics
```
GET    /dashboard                     # Get dashboard data
GET    /dashboard/stats              # Get user statistics
GET    /projects/<id>/stats         # Get project statistics
GET    /tasks/stats                 # Get task statistics
```

### Response Formats

All API endpoints return JSON responses with the following structure:

```json
{
    "success": true|false,
    "data": {
        // Response data
    },
    "message": "Success or error message",
    "errors": {
        // Validation errors if any
    }
}
```

### Authentication

API endpoints require authentication using session cookies. Protected routes will return a 401 status code if unauthorized.

### Error Codes

- 200: Success
- 201: Created
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Unprocessable Entity
- 500: Server Error

### Rate Limiting

API requests are limited to:
- 100 requests per minute for authenticated users
- 30 requests per minute for unauthenticated users

## Security

- Password hashing using Werkzeug
- CSRF protection
- Secure session management
- Role-based access control
- Input validation and sanitization

