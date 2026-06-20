import webbrowser
import sqlite3 
from flask import Flask,session, flash, render_template, request, redirect, url_for 
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Timer
from datetime import datetime, timedelta, date
from functools import wraps
import re

app = Flask(__name__) 
app.secret_key = "redbutterflies"

ADMIN_EMAIL = "codegirlr@hotmail.com"
app.jinja_env.globals['admin_email'] = ADMIN_EMAIL

#Time Formatting
@app.template_filter('format_time')
def format_time(value):
    try:
        dt = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        return dt.strftime("%I:%M %p — %d %b %Y")
    except:
        return value

users = []

# Database Connection
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

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

# CREATE CHILDCARE TABLES
def create_childcare_tables():
    conn = get_db_connection()

    #feeding table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feeding (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            amount INTEGER,
            notes TEXT
        )
    ''')

    # Sleep table 
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sleep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration TEXT NOT NULL,
            notes TEXT 
        )
    ''')
    # Nappy table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS nappy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            nappy_type TEXT NOT NULL,
            notes TEXT 
        )
    ''')

    conn.commit()
    conn.close()

#ROUTES  
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


# Email validation using regex
def is_valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9]+$'
    return re.match(email_regex, email)

# Password strength validation
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

        # Validate email
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
    conn = get_db_connection()
    if request.method == 'POST':

    # Feeds can only be inputted on the day and at that time and going back max three days
        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)

    # Validation to ensure entry must be within last 3 days        
        if time_dt < three_days_ago or time_dt > today:
                flash("Date input must be within the last three days.")
                return redirect(url_for('feeding'))

        time = request.form['time']
        feed_type = request.form['type']
        notes = request.form['notes']

        # If the type is a meal or snack, amount and unit are now shown in percentages
        if feed_type in ["Meal", "Snack"]:
                amount = request.form['percentage']
                unit = "%"

        else: 
            amount = request.form['amount']
            unit = request.form['unit']

        # Allow decimals, blocking negatives and zeros 
            try:
                if float(amount) <= 0:
                    flash("Amount must be greater than zero.")
                    return redirect(url_for('feeding'))
            except ValueError:
                flash("Amount must be a number.")
                return redirect(url_for('feeding'))

        conn.execute("INSERT INTO feeding (time, type, amount, unit, notes, user_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (time, feed_type, amount, unit, notes, session['user_id']))
        conn.commit()
   
    # ALWAYS show logs (GET order)
    logs = conn.execute(
        "SELECT * FROM feeding WHERE user_id = ? ORDER BY id DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('feeding.html', logs=logs)

# DELETE FROM FEEDING
@app.route('/feeding/delete/<int:id>', methods=['POST'])
@login_required
def delete_feeding(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM feeding WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('feeding'))

# UPDATE/EDIT FEEDING INPUT
@app.route('/feeding/edit/<int:id>', methods=['GET', 'POST'])
def edit_feeding(id):
    conn = get_db_connection()
    log = conn.execute(
        "SELECT * FROM feeding WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    ).fetchone()

    if not log:
        flash("Feeding entry not found.")
        conn.close()
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

    # Validation        
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
    
        conn.execute("""
            UPDATE feeding
            SET time = ?, type = ?, amount = ?, unit = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (time_dt, feed_type, amount, unit, notes, id, session['user_id']))

        conn.commit()
        conn.close()

        flash("Feeding entry updated.")
        return redirect(url_for('feeding'))

    conn.close()
    return render_template('edit_feeding.html', log=log)

# SLEEP ROUTE        
@app.route('/sleep', methods=['GET', 'POST'])
@login_required
def sleep():

    # Sleep can only be inputted on the day and going back max three days
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)

    max_date = today.strftime("%I:%M %p — %d %b %Y")
    min_date = three_days_ago.strftime("%I:%M %p — %d %b %Y")

    conn = get_db_connection()

    if request.method == 'POST':
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/feeding')
        
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


        conn.execute("INSERT INTO sleep (start_time, end_time, duration, notes, user_id) VALUES (?, ?, ?, ?, ?)",
                     (start, end, duration_str, notes, session['user_id']))
        conn.commit()

    logs = conn.execute(
        "SELECT * FROM sleep WHERE user_id = ? ORDER BY id DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('sleep.html',
                            logs=logs,
                            min_date=min_date,
                            max_date=max_date
                            )

# DELETE FROM SLEEP
@app.route('/sleep/delete/<int:id>', methods=['POST'])
@login_required
def delete_sleep(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM sleep WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('sleep'))

# UPDATE SLEEP 
@app.route('/edit/sleep/<int:id>', methods=['GET', 'POST'])
def edit_sleep(id):

    if 'user_id' not in session:
        return redirect ('/login')

    conn = get_db_connection()
    log = conn.execute(
        "SELECT * FROM sleep WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    ).fetchone()

    if not log:
        conn.close()
        return "Sleep entry not found."
    
    if request.method == 'POST':
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/sleep')
        
        start = request.form['start']
        end = request.form['end']
        notes = request.form['notes']

        start_dt = datetime.strptime(start, "%Y-%m-%dT%H:%M")
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M")

        # End time cannot be earlier than start time 
        if end_dt < start_dt:
            conn.close()
            error = "End time cannot be earlier than start time."
            return render_template('edit_sleep.html', log=log, error=error)

        duration = end_dt - start_dt
        total_minutes = duration.total_seconds() // 60
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        duration_str = f"{hours}h {minutes}m"

        conn.execute( """
            UPDATE sleep
            SET start_time = ?, end_time = ?, notes = ?, duration = ?
            WHERE id = ? AND user_id = ? 
        """, (start, end, notes, duration_str, id, session['user_id']))

        conn.commit()
        conn.close()
        
        flash("Sleep entry updated.")
        return redirect(url_for('sleep', log=log))

    conn.close()
    return render_template('edit_sleep.html', log=log)

# NAPPY ROUTE
@app.route('/nappy', methods=['GET', 'POST'])
@login_required
def nappy():
    conn = get_db_connection()
    if request.method == 'POST':

        time_str = request.form['time']
        time_dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

        today = datetime.now()
        three_days_ago = today - timedelta(days=3)

    # Validation to ensure entry must be within last 3 days        
        if time_dt < three_days_ago or time_dt > today:
                flash("Date input must be within the last three days.")
                return redirect(url_for('nappy'))

        time = request.form['time']
        nappy_type = request.form['type']
        notes = request.form['notes']

        conn.execute("INSERT INTO nappy (time, nappy_type, notes, user_id) VALUES (?, ?, ?, ?)",
                     (time, nappy_type, notes, session['user_id']))
        conn.commit()

    logs = conn.execute(
        "SELECT * FROM nappy WHERE user_id = ? ORDER BY id DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('nappy.html', logs=logs)

# DELETE FROM NAPPY 
@app.route('/nappy/delete/<int:id>', methods=['POST'])
@login_required
def delete_nappy(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM nappy WHERE id = ? AND user_id = ?", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('nappy'))

# UPDATE NAPPY
@app.route('/nappy/edit/<int:id>', methods=['GET', 'POST'])
def edit_nappy(id):

    if 'user_id' not in session:
        return redirect ('/login')
    
    conn = get_db_connection()
    log = conn.execute(
        "SELECT * FROM nappy WHERE id = ? AND user_id = ?",
        (id, session['user_id'])
    ).fetchone()

    if not log:
        conn.close()
        return "Nappy entry not found."
    
    if request.method == 'POST':
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/nappy')
        
        time_str = request.form['time']
        nappy_type = request.form['type']
        notes = request.form['notes']

        conn.execute("""
                UPDATE nappy
                SET time = ?, nappy_type = ?, notes = ?
                WHERE id =? AND  user_id = ?
                """, (time_str, nappy_type, notes, id, session['user_id']))
        
        conn.commit()
        conn.close()

        flash("Nappy entry updated.")
        return redirect ('/nappy')
    
    conn.close()
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
create_childcare_tables()

# RUN FLASK 
def open_browser():
    webbrowser.open_new('http://localhost:5000/')

def app_run_flask():
     Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
     app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

# Running the app with a custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes
app_run_flask() 

