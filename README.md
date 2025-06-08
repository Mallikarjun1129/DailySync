# Personal Task and Diary Management System

A comprehensive web application for managing tasks and personal diary entries with role-based access control and theme customization.

## Features

### Task Management
- Create, read, update, and delete tasks
- Set task priorities (High, Medium, Low)
- Track task status (Pending, In Progress, Completed)
- Set due dates for tasks
- Filter tasks by status and priority
- Search tasks by name or description

### Personal Diary
- Create and manage diary entries
- Add tags to entries for better organization
- Filter entries by date and tags
- Search through diary entries
- Calendar view for easy navigation

### User Management
- User registration and authentication
- Role-based access control (Student, Teacher, Business)
- Profile management
- Theme customization based on user role

### Theme Customization
- Role-specific themes
- Dark and light mode support
- Customizable color schemes
- Responsive design for all devices

## Technical Stack

### Backend
- **Framework**: Flask 3.0.2
- **Database**: MongoDB (PyMongo 4.6.2)
- **Authentication**: Flask-Login with bcrypt
- **Form Handling**: Flask-WTF 1.2.1
- **Email Validation**: email-validator 2.1.0

### Frontend
- **HTML5/CSS3**: Modern, responsive design
- **JavaScript**: Dynamic user interactions
- **Bootstrap**: UI components and grid system
- **Custom CSS**: Theme customization

## Project Structure

```
├── app.py              # Main application file
├── requirements.txt    # Project dependencies
├── static/            # Static assets
│   ├── css/          # Stylesheets
│   └── js/           # JavaScript files
└── templates/         # HTML templates
    ├── base.html     # Base template
    ├── index.html    # Dashboard
    ├── tasks/        # Task-related templates
    └── diary/        # Diary-related templates
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <project-directory>
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with the following variables:
```
MONGODB_URI=your_mongodb_connection_string
SECRET_KEY=your_secret_key
```

5. Run the application:
```bash
python app.py
```

## Usage

1. Register a new account or log in with existing credentials
2. Choose your role (Student, Teacher, or Business)
3. Access the dashboard to manage tasks and diary entries
4. Customize your theme preferences
5. Start managing your tasks and diary entries

## Features by Role

### Student
- Task management with academic focus
- Personal diary for reflections
- Light theme optimized for study sessions

### Teacher
- Task management for lesson planning
- Professional diary for teaching notes
- Balanced theme for classroom use

### Business
- Task management for project tracking
- Professional diary for meeting notes
- Dark theme optimized for office use

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask framework and its extensions
- MongoDB for database support
- Bootstrap for UI components
- All contributors and users of the application 