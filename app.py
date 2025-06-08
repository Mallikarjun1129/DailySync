from flask import Flask, render_template, request, redirect, url_for, Response, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# MongoDB configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/task_diary_db')
try:
    client = MongoClient(MONGODB_URI)
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    raise

db = client['task_diary_db']
tasks_collection = db['tasks']
users_collection = db['users']
diary_collection = db['diary']

# User authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Role-based access control decorator
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('login'))
            
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
            if not user or user.get('role') not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
@login_required
def index():
    try:
        # Get task statistics for the logged-in user
        total_tasks = tasks_collection.count_documents({'user_id': session['user_id']})
        pending_tasks = tasks_collection.count_documents({
            'user_id': session['user_id'],
            'status': 'pending'
        })
        total_diary_entries = diary_collection.count_documents({'user_id': session['user_id']})
        
        return render_template('index.html',
                             total_tasks=total_tasks,
                             pending_tasks=pending_tasks,
                             total_diary_entries=total_diary_entries)
    except Exception as e:
        print(f"Error in index route: {e}")
        flash('An error occurred while loading the dashboard.', 'error')
        return render_template('index.html',
                             total_tasks=0,
                             pending_tasks=0,
                             total_diary_entries=0)

@app.route('/tasks')
@login_required
def list_tasks():
    try:
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')
        sort_by = request.args.get('sort', 'due_date')
        
        query = {'user_id': session['user_id']}
        if search_query:
            query['name'] = {'$regex': search_query, '$options': 'i'}
        if status_filter:
            query['status'] = status_filter
        if priority_filter:
            query['priority'] = priority_filter
        
        tasks_list = list(tasks_collection.find(query).sort(sort_by, 1))
        for task in tasks_list:
            task['_id'] = str(task['_id'])
        
        return render_template('tasks.html', tasks=tasks_list)
    except Exception as e:
        print(f"Error in list_tasks route: {e}")
        flash('An error occurred while loading tasks.', 'error')
        return redirect(url_for('index'))

@app.route('/tasks/overdue')
@login_required
def overdue_tasks():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        overdue_tasks_list = list(tasks_collection.find({
            'user_id': session['user_id'],
            'due_date': {'$lt': today},
            'status': 'pending'
        }))
        for task in overdue_tasks_list:
            task['_id'] = str(task['_id'])
        return render_template('tasks.html', tasks=overdue_tasks_list, title='Overdue Tasks')
    except Exception as e:
        print(f"Error in overdue_tasks route: {e}")
        flash('An error occurred while loading overdue tasks.', 'error')
        return redirect(url_for('list_tasks'))

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        try:
            task = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'due_date': request.form.get('due_date'),
                'priority': request.form.get('priority'),
                'status': 'pending',
                'user_id': session['user_id'],
                'created_at': datetime.now()
            }
            tasks_collection.insert_one(task)
            flash('Task added successfully!', 'success')
            return redirect(url_for('list_tasks'))
        except Exception as e:
            print(f"Error in add_task route: {e}")
            flash('An error occurred while adding the task.', 'error')
    
    return render_template('add_task.html')

@app.route('/edit_task/<task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    try:
        print(f"Editing task {task_id} for user {session['user_id']}")
        
        # Validate task_id format
        try:
            task_object_id = ObjectId(task_id)
        except Exception as e:
            print(f"Invalid task ID format: {e}")
            flash('Invalid task ID format.', 'error')
            return redirect(url_for('list_tasks'))
        
        # Get task with user validation
        task = tasks_collection.find_one({'_id': task_object_id, 'user_id': session['user_id']})
        if not task:
            print(f"Task not found or unauthorized access attempt: {task_id}")
            flash('Task not found or you do not have permission to edit it.', 'error')
            return redirect(url_for('list_tasks'))
        
        if request.method == 'POST':
            try:
                # Validate form data
                name = request.form.get('name')
                description = request.form.get('description')
                due_date = request.form.get('due_date')
                priority = request.form.get('priority')
                status = request.form.get('status')
                
                if not all([name, description, due_date, priority, status]):
                    flash('All fields are required.', 'error')
                    return render_template('edit_task.html', task=task)
                
                # Update task
                update_result = tasks_collection.update_one(
                    {'_id': task_object_id, 'user_id': session['user_id']},
                    {'$set': {
                        'name': name,
                        'description': description,
                        'due_date': due_date,
                        'priority': priority,
                        'status': status,
                        'updated_at': datetime.now()
                    }}
                )
                
                if update_result.modified_count == 0:
                    print(f"Task update failed: {task_id}")
                    flash('Failed to update task. Please try again.', 'error')
                else:
                    print(f"Task updated successfully: {task_id}")
                    flash('Task updated successfully!', 'success')
                    return redirect(url_for('list_tasks'))
                
            except Exception as e:
                print(f"Error updating task: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                flash('An error occurred while updating the task.', 'error')
        
        # Convert ObjectId to string for template
        task['_id'] = str(task['_id'])
        return render_template('edit_task.html', task=task)
        
    except Exception as e:
        print(f"Error in edit_task route: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash('An error occurred while editing the task.', 'error')
        return redirect(url_for('list_tasks'))

@app.route('/delete_task/<task_id>')
@login_required
def delete_task(task_id):
    try:
        result = tasks_collection.delete_one({'_id': ObjectId(task_id), 'user_id': session['user_id']})
        if result.deleted_count == 0:
            flash('Task not found or you do not have permission to delete it.', 'error')
        else:
            flash('Task deleted successfully!', 'success')
    except Exception as e:
        print(f"Error in delete_task route: {e}")
        flash('An error occurred while deleting the task.', 'error')
    return redirect(url_for('list_tasks'))

@app.route('/update_task/<task_id>', methods=['POST'])
@login_required
def update_task(task_id):
    try:
        new_status = request.form['status']
        result = tasks_collection.update_one(
            {'_id': ObjectId(task_id), 'user_id': session['user_id']},
            {'$set': {'status': new_status}}
        )
        if result.modified_count == 0:
            flash('Task not found or you do not have permission to update it.', 'error')
        else:
            flash('Task status updated successfully!', 'success')
    except Exception as e:
        print(f"Error in update_task route: {e}")
        flash('An error occurred while updating the task.', 'error')
    return redirect(url_for('list_tasks'))

@app.route('/download_tasks')
@login_required
def download_tasks():
    try:
        task_list = list(tasks_collection.find({'user_id': session['user_id']}))
        task_text = ''
        for task in task_list:
            task_text += f'Task: {task["name"]}, Description: {task["description"]}, Due Date: {task["due_date"]}, Priority: {task["priority"]}, Status: {task["status"]}\n'
        
        return Response(
            task_text,
            mimetype='text/plain',
            headers={'Content-Disposition': 'attachment; filename=tasks.txt'}
        )
    except Exception as e:
        print(f"Error in download_tasks route: {e}")
        flash('An error occurred while downloading tasks.', 'error')
        return redirect(url_for('list_tasks'))

@app.route('/diary')
@login_required
def diary():
    try:
        print(f"Accessing diary for user_id: {session['user_id']}")
        
        # Get date filter if provided
        date_filter = request.args.get('date', '')
        tag_filter = request.args.get('tag', '')
        
        # Build query
        query = {'user_id': session['user_id']}
        if date_filter:
            query['date'] = date_filter
        if tag_filter:
            query['tags'] = tag_filter
            
        print(f"Query: {query}")
        
        # Get entries with proper date sorting
        entries = list(diary_collection.find(query).sort('date', -1))
        print(f"Found {len(entries)} entries")
        
        # Convert ObjectId to string for each entry
        for entry in entries:
            entry['_id'] = str(entry['_id'])
            # Ensure date is in string format
            if isinstance(entry.get('date'), datetime):
                entry['date'] = entry['date'].strftime('%Y-%m-%d')
        
        # Collect all unique tags for the tag filter dropdown
        tags_set = set()
        for entry in entries:
            if 'tags' in entry and entry['tags']:
                tags_set.update(entry['tags'])
        tags = sorted(list(tags_set))
        
        return render_template('diary.html', entries=entries, tags=tags)
    except Exception as e:
        print(f"Error in diary route: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash('An error occurred while loading diary entries.', 'error')
        return redirect(url_for('index'))

@app.route('/add_diary', methods=['GET', 'POST'])
@login_required
def add_diary():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            entry = request.form.get('entry')
            date = request.form.get('date') or datetime.now().strftime('%Y-%m-%d')
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            diary_entry = {
                'user_id': session['user_id'],
                'title': title,
                'entry': entry,
                'date': date,
                'tags': tags,
                'created_at': datetime.now()
            }
            diary_collection.insert_one(diary_entry)
            flash('Diary entry added successfully!', 'success')
            return redirect(url_for('diary'))
        except Exception as e:
            print(f"Error in add_diary route: {e}")
            flash('An error occurred while adding the diary entry.', 'error')
    
    return render_template('add_diary.html')

@app.route('/edit_diary/<entry_id>', methods=['GET', 'POST'])
@login_required
def edit_diary(entry_id):
    try:
        entry = diary_collection.find_one({'_id': ObjectId(entry_id), 'user_id': session['user_id']})
        if not entry:
            flash('Diary entry not found or you do not have permission to edit it.', 'error')
            return redirect(url_for('diary'))
        
        if request.method == 'POST':
            tags = request.form.get('tags', '').split(',')
            tags = [tag.strip() for tag in tags if tag.strip()]
            
            diary_collection.update_one(
                {'_id': ObjectId(entry_id), 'user_id': session['user_id']},
                {'$set': {
                    'title': request.form.get('title'),
                    'entry': request.form.get('entry'),
                    'date': request.form.get('date'),
                    'tags': tags,
                    'updated_at': datetime.now()
                }}
            )
            flash('Diary entry updated successfully!', 'success')
            return redirect(url_for('diary'))
        
        entry['_id'] = str(entry['_id'])
        return render_template('edit_diary.html', entry=entry)
    except Exception as e:
        print(f"Error in edit_diary route: {e}")
        flash('An error occurred while editing the diary entry.', 'error')
        return redirect(url_for('diary'))

@app.route('/delete_diary/<entry_id>')
@login_required
def delete_diary(entry_id):
    try:
        result = diary_collection.delete_one({'_id': ObjectId(entry_id), 'user_id': session['user_id']})
        if result.deleted_count == 0:
            flash('Diary entry not found or you do not have permission to delete it.', 'error')
        else:
            flash('Diary entry deleted successfully!', 'success')
    except Exception as e:
        print(f"Error in delete_diary route: {e}")
        flash('An error occurred while deleting the diary entry.', 'error')
    return redirect(url_for('diary'))

@app.route('/search_diary')
@login_required
def search_diary():
    try:
        query = request.args.get('query', '')
        if not query:
            return redirect(url_for('diary'))
        
        entries = list(diary_collection.find({
            'user_id': session['user_id'],
            '$or': [
                {'title': {'$regex': query, '$options': 'i'}},
                {'entry': {'$regex': query, '$options': 'i'}},
                {'tags': {'$regex': query, '$options': 'i'}}
            ]
        }).sort('date', -1))
        
        for entry in entries:
            entry['_id'] = str(entry['_id'])
        
        return render_template('diary.html', entries=entries, search_query=query)
    except Exception as e:
        print(f"Error in search_diary route: {e}")
        flash('An error occurred while searching diary entries.', 'error')
        return redirect(url_for('diary'))

@app.route('/export_diary')
@login_required
def export_diary():
    try:
        entries = list(diary_collection.find({'user_id': session['user_id']}).sort('date', -1))
        diary_text = ''
        for entry in entries:
            diary_text += f'Date: {entry["date"]}\n'
            diary_text += f'Title: {entry["title"]}\n'
            diary_text += f'Entry: {entry["entry"]}\n'
            if entry.get('tags'):
                diary_text += f'Tags: {", ".join(entry["tags"])}\n'
            diary_text += '\n---\n\n'
        
        return Response(
            diary_text,
            mimetype='text/plain',
            headers={'Content-Disposition': 'attachment; filename=diary.txt'}
        )
    except Exception as e:
        print(f"Error in export_diary route: {e}")
        flash('An error occurred while exporting diary entries.', 'error')
        return redirect(url_for('diary'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            role = request.form.get('role', 'student')
            
            if users_collection.find_one({'email': email}):
                flash('Email already registered.', 'error')
                return redirect(url_for('signup'))
            
            hashed_password = generate_password_hash(password)
            user = {
                'email': email,
                'password': hashed_password,
                'role': role,
                'created_at': datetime.now()
            }
            users_collection.insert_one(user)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Error in signup route: {e}")
            flash('An error occurred during registration.', 'error')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = users_collection.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                session['user_id'] = str(user['_id'])
                session['role'] = user.get('role', 'student')
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'error')
        except Exception as e:
            print(f"Error in login route: {e}")
            flash('An error occurred during login.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        print(f"Accessing dashboard for user_id: {session['user_id']}")
        
        # Get user data
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        if not user:
            print(f"User not found for id: {session['user_id']}")
            flash('User not found', 'error')
            return redirect(url_for('login'))

        print(f"Found user with role: {user.get('role')}")

        # Get task statistics with proper error handling
        try:
            total_tasks = tasks_collection.count_documents({'user_id': session['user_id']})
            pending_tasks = tasks_collection.count_documents({
                'user_id': session['user_id'],
                'status': 'pending'
            })
            completed_tasks = tasks_collection.count_documents({
                'user_id': session['user_id'],
                'status': 'completed'
            })
            print(f"Task stats - Total: {total_tasks}, Pending: {pending_tasks}, Completed: {completed_tasks}")
        except Exception as e:
            print(f"Error getting task statistics: {str(e)}")
            print(f"Error type: {type(e)}")
            total_tasks = pending_tasks = completed_tasks = 0

        # Get diary statistics with proper error handling
        try:
            total_entries = diary_collection.count_documents({'user_id': session['user_id']})
            this_month = datetime.now().strftime('%Y-%m')
            this_month_entries = diary_collection.count_documents({
                'user_id': session['user_id'],
                'date': {'$regex': f'^{this_month}'}
            })
            print(f"Diary stats - Total: {total_entries}, This month: {this_month_entries}")
        except Exception as e:
            print(f"Error getting diary statistics: {str(e)}")
            print(f"Error type: {type(e)}")
            total_entries = this_month_entries = 0

        # Get priority tasks with proper error handling
        try:
            priority_tasks = list(tasks_collection.find({
                'user_id': session['user_id'],
                'status': 'pending'
            }).sort('due_date', 1).limit(5))
            
            # Convert ObjectId to string for each task
            for task in priority_tasks:
                task['_id'] = str(task['_id'])
                # Ensure date is in string format
                if isinstance(task.get('due_date'), datetime):
                    task['due_date'] = task['due_date'].strftime('%Y-%m-%d')
            print(f"Found {len(priority_tasks)} priority tasks")
        except Exception as e:
            print(f"Error getting priority tasks: {str(e)}")
            print(f"Error type: {type(e)}")
            priority_tasks = []

        # Set theme based on user role
        theme = 'light'  # Default theme
        if user.get('role') == 'student':
            theme = 'student'
        elif user.get('role') == 'teacher':
            theme = 'teacher'
        elif user.get('role') == 'business':
            theme = 'business'

        # Prepare common data for all dashboard templates
        dashboard_data = {
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'completed_tasks': completed_tasks,
            'total_entries': total_entries,
            'this_month_entries': this_month_entries,
            'priority_tasks': priority_tasks,
            'theme': theme
        }

        # Render appropriate dashboard template based on role
        if user.get('role') == 'student':
            return render_template('student_dashboard.html', **dashboard_data)
        elif user.get('role') == 'teacher':
            return render_template('teacher_dashboard.html', **dashboard_data)
        elif user.get('role') == 'business':
            return render_template('business_dashboard.html', **dashboard_data)
        else:
            print(f"Invalid role: {user.get('role')}")
            flash('Invalid user role', 'error')
            return redirect(url_for('login'))
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 