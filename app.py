import webbrowser
import sqlite3 
from flask import Flask,session, flash, render_template, request, redirect, url_for 
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Timer
from functools import wraps
import re

app = Flask(__name__) 
app.secret_key = "redbutterflies"

ADMIN_EMAIL = "codegirlr@hotmail.com"
app.jinja_env.globals['admin_email'] = ADMIN_EMAIL

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
    return render_template('home.html')  # Render the home.html template and pass the users list to it

@app.route('/about')
def about():
    return render_template('about.html')  # Render the about.html template

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
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, password) VALUES (?, ?, ?, ?)",
                (first_name, last_name, email, hashed_password)
            )
            conn.commit()
            
            flash("Registeration Successful!")
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
            
            flash(f"Login Successful! Welcome, {first_name}!")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.")
            return render_template('login.html')
        
    return render_template('login.html')  # Render the data.html template and pass the users list to it

# FEEDING ROUTE
@app.route('/feeding', methods=['GET', 'POST'])
@login_required
def feeding():
    conn = get_db_connection()

    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        time = request.form['time']
        amount = int(request.form['amount'])
        notes = request.form['notes']

        conn.execute("INSERT INTO feeding (time, amount, notes) VALUES (?, ?, ?)",
                    (time, amount, notes))
        conn.commit()
        
    # ALWAYS fetch logs (GET or POST)
    logs = conn.execute("SELECT * FROM feeding ORDER BY id DESC").fetchall()
    conn.close()

    return render_template('feeding.html', logs=logs)

# SLEEP ROUTE        
@app.route('/sleep', methods=['GET', 'POST'])
@login_required
def sleep():
    conn = get_db_connection()

    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        start = request.form['start']
        end = request.form['end']
        notes = request.form['notes']

        conn.execute("INSERT INTO sleep (start_time, end_time, notes) VALUES (?, ?, ?)",
                     (start, end, notes))
        conn.commit()

    logs = conn.execute("SELECT * FROM sleep ORDER BY id DESC").fetchall()
    conn.close()

    return render_template('sleep.html', logs=logs)

# NAPPY ROUTE
@app.route('/nappy', methods=['GET', 'POST'])
@login_required
def nappy():
    conn = get_db_connection()

    if 'user_email' not in session:
        flash("Please log in first.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        time = request.form['time']
        nappy_type = request.form['type']
        notes = request.form['notes']

        conn.execute("INSERT INTO nappy (time, nappy_type, notes) VALUES (?, ?, ?)",
                     (time, nappy_type, notes))
        conn.commit()
    logs = conn.execute("SELECT * FROM nappy ORDER BY id DESC").fetchall()
    conn.close()

    return render_template('nappy.html', logs=logs)

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

