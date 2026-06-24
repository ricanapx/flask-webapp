import webbrowser
import sqlite3 
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from flask import Flask,session, flash, render_template, request, redirect, url_for 
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Timer
from datetime import datetime, timedelta, date
from functools import wraps
import re
import os

load_dotenv()

app = Flask(__name__) 
app.secret_key = "redbutterflies"

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["Childcare_Tracking"]

users = []
# Database Connection
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


ADMIN_EMAIL = "codegirlr@hotmail.com"
app.jinja_env.globals['admin_email'] = ADMIN_EMAIL
    
# CREATE USERS TABLE
def create_users_table():
    conn = sqlite3.connect('users.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )         
        ''')
    conn.commit()
    conn.close()

#Time Formatting
@app.template_filter('format_time')
def format_time(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return dt.strftime("%I:%M %p — %d %b %Y")
    except:
        return value

@app.route('/') 
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')  # Render the home.html template and pass the users list to it

@app.route('/about')
def about():
    return render_template('about.html')  # Render the about.html template
    
# Decorator for extra protection. 
# Ensures that anyone who comes across certain pages must be logged in and displays the message too.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view that page.")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9]+$'
    return re.match(email_regex, email)

def is_password_strong(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

# REGISTER USER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':    
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        if not is_valid_email(email):
            flash('Invalid email formail. PLease enter a valid email.')
            return render_template('register.html')
        
        if not is_password_strong(password):
            flash('Password must be at least 8 characters long, include at least one uppercase letter, one lowercase letter and one number.')
            return render_template('register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   email=email)

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                (first_name, last_name, email, hashed_password)
            )
            conn.commit()
                        
            #Log in user after registering.
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            session['user_id'] = user_id
            session['user_email'] = email
            session['first_name'] = first_name

            flash(f"Registeration Successful! Welcome, {first_name}!")
            return redirect(url_for('home'))  # Redirect to the home page after registration

        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template('register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   email=email)
        
        finally:
            conn.close()
            
    return render_template('register.html')  # Render the register.html template for GET requests

# DASHBOARD - allows users to see summary of daily input
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    today = date.today()

    # connect to the db
    conn = get_db_connection()

    # Fetch today's logs 
    feeds =  conn.execute(
        "SELECT * FROM feeding WHERE user_id = ? AND date(time) = ?",
        (user_id, today)
    ).fetchall()
    
    sleeps = conn.execute(
        "SELECT * FROM sleep WHERE user_id = ? AND date(start_time) = ?",
        (user_id, today)
    ).fetchall()

    nappies = conn.execute(
        "SELECT * FROM nappy WHERE user_id = ? AND date(time) = ?",
        (user_id, today)
    ).fetchall()

    conn.close()

    return render_template('dashboard.html',
                           feeds=feeds,
                           sleeps=sleeps,
                           nappies=nappies)

# LOG USERS IN
@app.route('/login', methods= ['GET', 'POST'])
def login(): 
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            first_name = user['first_name']
            
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['first_name'] = user['first_name']
            
            flash(f"Login Successful!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.")
            return render_template('login.html')
        
    return render_template('login.html')  # Render the data.html template and pass the users list to it

# FEEDING ROUTE
@app.route('/feeding', methods=['GET', 'POST'])
@login_required
def feeding():
  
    if request.method == 'POST':

        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)

    # Validation       
        if time_dt < three_days_ago or time_dt > today:
                flash("Date input must be within the last three days.")
                return redirect(url_for('feeding'))

        time = request.form['time']
        feed_type = request.form['type']
        notes = request.form['notes']

        if feed_type in ["Meal", "Snack"]:
                amount = request.form['percentage']
                unit = "%"

        else: 
            amount = request.form['amount']
            unit = request.form['unit']

            try:
                if float(amount) <= 0:
                    flash("Amount must be greater than zero.")
                    return redirect(url_for('feeding'))
            except ValueError:
                flash("Amount must be a number.")
                return redirect(url_for('feeding'))

        db.feeding_logs.insert_one({
            "time": time_dt,
            "type": feed_type,
            "amount": amount,
            "unit": unit,
            "notes": notes,
            "user_id": session['user_id']
        })

        return redirect(url_for('feeding'))
   
    # ALWAYS show logs (GET order)
    logs = list(
        db.feeding_logs
        .find({"user_id": session['user_id']})
        .sort("_id", -1)
    )

    return render_template('feeding.html', logs=logs)

# DELETE FROM FEEDING
@app.route('/feeding/delete/<id>', methods=['POST'])
@login_required
def delete_feeding(id):

    result = db.feeding_logs.delete_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if result.deleted_count == 0:
        flash("Could not delete entry.")
    else:
        flash("Feeding entry deleted.")

    return redirect(url_for('feeding'))

# UPDATE/EDIT FEEDING INPUT
@app.route('/feeding/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_feeding(id):

    log = db.feeding_logs.find_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if not log:
        flash("Feeding entry not found.")
        return redirect(url_for('feeding'))
    
    if request.method == 'POST':
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/feeding')
        
        # Time update/edit
        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)
        
        if time_dt < three_days_ago or time_dt > today:
            flash("Date input must be within the last three days.")
            return redirect(url_for('edit_feeding', id=id))
    
        feed_type = request.form['type']
        notes = request.form['notes']

    # Meal/snack vs drink
        if feed_type in ["Meal", "Snack"]:
            amount = request.form['percentage']
            unit = "%"
        else: 
            amount = request.form['amount']
            unit = request.form['unit']
        
            try:
                if float(amount) <= 0:
                    flash("Amount must be greater than zero.")
                    return redirect(url_for('edit_feeding', id=id))
            except ValueError:
                flash("Amount must be a number.")
                return redirect(url_for('edit_feeding', id=id))
    
        db.feeding_logs.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "time": time_str,
                "type": feed_type,
                "amount": amount,
                "unit": unit,
                "notes": notes
            }}
        )

        flash("Feeding entry updated.")
        return redirect(url_for('feeding'))


    return render_template('edit_feeding.html', log=log)

# SLEEP ROUTE        
@app.route('/sleep', methods=['GET', 'POST'])
@login_required
def sleep():
    logs = list(
        db.sleep_logs
        .find({"user_id": session['user_id']})
        .sort("_id", -1)
    )

    today = datetime.now()
    three_days_ago = today - timedelta(days=3)

    max_date = today.strftime("%Y-%m-%dT%H:%M")
    min_date = three_days_ago.strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect(url_for('sleep'))
        
        start = request.form['start']
        end = request.form['end']
        notes = request.form['notes']

        # Calculate duration of sleep
        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M")

        # Validation to ensure entry must be within last 3 days
        if start_dt < three_days_ago or start_dt > today:
            flash("Start time must be within the last three days.")
            return redirect(url_for('sleep'))
        
        if end_dt < three_days_ago or end_dt > today:
            flash("End time must be within the last three days.")
            return redirect(url_for('sleep'))

        # Overnight sleep being included in the duration
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        # Actual duration calculation 
        duration = end_dt - start_dt
        total_minutes = duration.total_seconds() // 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        duration_str = f"{hours}h {minutes}m"

        # Block sleep longer than 16 hours (16 hour blocks not a daily limit)
        if duration > timedelta(hours=16):
            flash("Sleep duration cannot exceed 16 hours.")
            return redirect(url_for('sleep'))
        
        db.sleep_logs.insert_one({
            "start_time": start,
            "end_time": end,
            "duration": duration_str,
            "notes": notes,
            "user_id": session['user_id']
        })

    logs = list(
        db.sleep_logs
        .find({"user_id": session['user_id']})
        .sort("_id", -1)
    )

    return render_template('sleep.html',
                            logs=logs,
                            min_date=min_date,
                            max_date=max_date
                            )

# DELETE FROM SLEEP
@app.route('/sleep/delete/<id>', methods=['POST'])
@login_required
def delete_sleep(id):

    result = db.sleep_logs.delete_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if result.deleted_count == 0:
        flash("Could not delete sleep entry.")
    else:
        flash("Sleep entry deleted.")

    return redirect(url_for('sleep'))

# UPDATE SLEEP 
@app.route('/edit/sleep/<id>', methods=['GET', 'POST'])
@login_required
def edit_sleep(id):

    log = db.sleep_logs.find_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if not log:
        flash("Sleep entry not found.")
        return redirect(url_for('sleep'))

    today = datetime.now()
    three_days_ago = today - timedelta(days=3)

    max_date = today.strftime("%Y-%m-%dT%H:%M")
    min_date = three_days_ago.strftime("%Y-%m-%dT%H:%M")

    if request.method == 'POST':
        
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect(url_for('sleep'))
        
        start = request.form['start']
        end = request.form['end']
        notes = request.form['notes']

        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M")

        if start_dt < three_days_ago or start_dt > today:
            flash("Start time must be within the last three days.")
            return redirect(url_for('edit_sleep', id=id))

        if end_dt < three_days_ago or end_dt > today:
            flash("End time must be within the last three days.")
            return redirect(url_for('edit_sleep', id=id))
                
        if end_dt < start_dt:
            end_dt += timedelta(days=1)

        duration = end_dt - start_dt
        total_minutes = duration.total_seconds() // 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        duration_str = f"{hours}h {minutes}m"

        if duration > timedelta(hours=16):
            flash("Sleep duration cannot exceed 16 hours.")
            return redirect(url_for('edit_sleep', id=id))
        
        db.sleep_logs.update_one(
            {"_id": ObjectId(id), "user_id": session['user_id']},
            {"$set": {
                "start_time": start,
                "end_time": end,
                "duration": duration_str,
                "notes": notes
            }}
        )
        
        flash("Sleep entry updated.")
        return redirect(url_for('sleep', log=log))

    return render_template(
        'edit_sleep.html', 
        log=log,
        min_date=min_date,
        max_date=max_date
    )

# NAPPY ROUTE
@app.route('/nappy', methods=['GET', 'POST'])
@login_required
def nappy():

    if request.method == 'POST':

        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)

    # Validation to ensure entry must be within last 3 days        
        if time_dt < three_days_ago or time_dt > today:
            flash("Date input must be within the last three days.")
            return redirect(url_for('nappy'))

        nappy_type = request.form['type']
        notes = request.form['notes']

        db.nappy_logs.insert_one({
            "user_id": session['user_id'],            
            "time": time_dt,
            "type": nappy_type,
            "notes": notes,
        })

    logs = list(
        db.nappy_logs
        .find({"user_id": session['user_id']})
        .sort("_id", -1)
    )

    return render_template('nappy.html', logs=logs)

# DELETE FROM NAPPY 
@app.route('/nappy/delete/<id>', methods=['POST'])
@login_required
def delete_nappy(id):

    result = db.nappy_logs.delete_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if result.deleted_count == 0:
        flash("Could not delete nappy entry.")
    else:
        flash("Nappy entry deleted.")

    return redirect(url_for('nappy'))

# UPDATE NAPPY
@app.route('/nappy/edit/<id>', methods=['GET', 'POST'])
@login_required
def edit_nappy(id):

    if 'user_id' not in session:
        return redirect ('/login')
    
    log = db.nappy_logs.find_one({
        "_id": ObjectId(id),
        "user_id": session['user_id']
    })

    if not log:
        flash("Nappy entry not found.")
        return redirect(url_for('nappy'))

    
    if request.method == 'POST':

        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/nappy')
        
        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)

        # Validation
        if time_dt < three_days_ago or time_dt > today:
            flash("Date input must be within the last three days.")
            return redirect(url_for('edit_nappy', id=id))
        
        nappy_type = request.form['type']
        notes = request.form['notes']

        db.nappy_logs.update_one(
            {"_id": ObjectId(id), "user_id": session['user_id']},
            {"$set": {
            "time": time_dt,
            "type": nappy_type,
            "notes": notes,
            }}
        )

        flash("Nappy entry updated.")
        return redirect ('/nappy')
    

    return render_template ('edit_nappy.html', log=log)

# Admin Route
@app.route('/admin')
@login_required
def admin():
    # To check user is logged in
    if 'user_email' not in session:
        flash("You must be logged in to view this page.")
        return redirect(url_for('login'))
    
    # To check if user is admin
    if session['user_email'] != ADMIN_EMAIL:
        flash("You do not have permission to view this page.")
        return redirect(url_for('home'))
    
    # Fetch all users
    conn = get_db_connection()
    users = conn.execute("SELECT first_name, last_name, email, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()

    return render_template('admin.html', users=users)

@app.route('/contact')
def contact():
    return render_template('contact.html')  # Render the contact.html template

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))

# Run table creation
create_users_table()

# RUN FLASK 
def open_browser():
    webbrowser.open_new('http://localhost:5000/')

def app_run_flask():
     Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
     app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

# Running the app with a custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes
app_run_flask() 

