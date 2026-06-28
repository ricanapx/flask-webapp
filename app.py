import webbrowser
import sqlite3 
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from flask import Flask,session, flash, render_template, request, redirect, url_for 
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Timer
from datetime import datetime, timedelta, date, time
from functools import wraps
import re
import os

load_dotenv()

app = Flask(__name__) 
app.secret_key = "redbutterflies"

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["Childcare_Tracking"]
sleep_logs = db["sleep_logs"]

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
    
def format_dob(date_string):
    if not date_string:
        return None
    try:
        dt = datetime.strptime(date_string, "%Y-%m-%d")
        return dt.strftime("%d %B %Y") 
    except:
        return date_string
    
def calculate_age(date_string):
    if not date_string:
        return None
    try:
        dob = datetime.strptime(date_string, "%Y-%m-%d").date()
        today = date.today()

        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day

        if days < 0:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        if years < 1:
            return f"{months} months"
        return f"{years} years {months} months"
    except:
        return None
    
def get_child_stage(date_string):
    if not date_string:
        return None
    try:
        dob = datetime.strptime(date_string, "%Y-%m-%d").date()
        today = date.today()

        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day

        if days < 0:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        total_months = years * 12 + months

        if total_months < 1:
            stage = "Newborn"
        elif total_months < 6:
            stage = "Young Infant"
        elif total_months < 12:
            stage = "Older Infant"
        elif total_months < 36:
            stage = "Toddler"
        elif total_months < 60:
            stage = "Preschooler"
        elif total_months < 96:
            stage = "Early School Age"
        else:
            stage = "Child"

        return f"{stage}"
    except:
        return None

    
def format_member_since(datetime_string):
    if not datetime_string:
        return None
    try:
        dt = datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %B %Y")
    except:
        return datetime_string

    
# Greeting
def get_greeting():
    current_hour = datetime.now().hour

    if 0 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour <= 18:
        return "Good afternoon"
    else:
        return "Good evening"

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

@app.route('/') 
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')  

@app.route('/about')
def about():
    return render_template('about.html')  

# REGISTER USER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':    
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        username = request.form.get('username')
       
        if username == "":
            username = None

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

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()

        try:
            conn.execute(
                "INSERT INTO users (first_name, last_name, email, password, username, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (first_name, last_name, email, hashed_password, username, created_at)
            )
            conn.commit()
             
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            session['user_id'] = user_id
            session['user_email'] = email
            session['first_name'] = first_name

            flash("Account created! Please complete your profile.")
            return redirect(url_for('setup_parent'))


        except sqlite3.IntegrityError:
            flash("Email already registered.")
            return render_template('register.html',
                                   first_name=first_name,
                                   last_name=last_name,
                                   email=email)
        
        finally:
            conn.close()
            
    return render_template('register.html')  

@app.route('/setup_parent', methods=['GET', 'POST'])
@login_required
def setup_parent():
    user_id = session.get("user_id")

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    
    if request.method == "POST":
        username = request.form.get("username")
        parent_dob = request.form.get("parent_dob")
        parent_gender = request.form.get("parent_gender")

        conn.execute("""
            UPDATE users SET username = ?, parent_dob = ?, parent_gender = ? 
            WHERE id = ?
        """, (username, parent_dob, parent_gender, user_id))

        conn.commit()
        conn.close()

        return redirect(url_for('setup_child'))
    
    conn.close()
    return render_template("setup_parent.html", user=user)

@app.route('/setup_child', methods=['GET', 'POST'])
@login_required
def setup_child():
    user_id = session.get("user_id")

    conn = get_db_connection()
    child = conn.execute("SELECT * FROM children WHERE user_id = ?", (user_id,)).fetchone()

    if request.method == "POST":
        child_name = request.form.get("child_name")
        child_dob = request.form.get("child_dob")
        child_gender = request.form.get("child_gender")

        if child is None:
            conn.execute("""
                INSERT INTO children (user_id, child_name, child_dob, child_gender, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (user_id, child_name, child_dob, child_gender))
        else:
            conn.execute("""
                UPDATE children
                SET child_name = ?, child_dob = ?, child_gender = ?
                WHERE user_id = ?
            """, (child_name, child_dob, child_gender, user_id))

        conn.commit()
        conn.close()

        flash("Profile setup complete!")
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template("setup_child.html", child=child)

@app.route('/login', methods= ['GET', 'POST'])
def login(): 
    if request.method == 'POST':
        identifier = request.form.get("identifier")
        password = request.form.get("password")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            (identifier, identifier)
        ).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            first_name = user['first_name']
            
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['first_name'] = user['first_name']
 
            session['username'] = user['username']

            if user['username'] is None:
                flash("Please complete your profile.")
                return redirect(url_for('setup_parent'))

            conn = get_db_connection()
            child = conn.execute(
                "SELECT * FROM children WHERE user_id = ?",
                (user['id'],)
            ).fetchone()
            conn.close()

            if child is None and user['first_login'] == 1:
                return redirect(url_for('setup_parent'))
            
            flash(f"Login Successful!")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password.")
            return render_template('login.html')
         
    return render_template('login.html') 

@app.route('/parent')
@login_required
def parent_profile():
    user_id = session.get("user_id")

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    formatted_dob = format_dob(user['parent_dob'])
    parent_age = calculate_age(user['parent_dob'])
    member_since = format_member_since(user['created_at'])

    return render_template(
        "parent_profile.html",
        user=user,
        formatted_dob=formatted_dob,
        parent_age=parent_age,
        member_since=member_since
    )

# Edit parent profile 
@app.route('/edit_parent', methods=['GET', 'POST'])
@login_required
def edit_parent():
    user_id = session.get("user_id")

    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if request.method == "POST":
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/parent')

        email = request.form.get("email")
        username = request.form.get("username")
        parent_dob = request.form.get("parent_dob")
        parent_gender = request.form.get("parent_gender")
    

        existing = conn.execute(
            "SELECT * FROM users WHERE username = ? AND id != ?",
            (username, session['user_id'])
        ).fetchone()

        if existing:
            flash("Username already exists")
            conn.close()
            return redirect(url_for('parent_profile'))

        conn.execute("""
            UPDATE users
            SET email = ?, username = ?, parent_dob = ?, parent_gender = ?
            WHERE id = ?
        """, (email, username, parent_dob, parent_gender, user_id))

        conn.commit()
        conn.close()

        session['username'] = username

        flash("Profile updated successfully.")
        return redirect(url_for('parent_profile'))

    conn.close()
    return render_template("edit_parent.html", user=user)

# Child profile route
@app.route('/child')
@login_required
def child_profile():
    user_id = session.get("user_id")

    conn = get_db_connection()
    child = conn.execute(
        "SELECT * FROM children WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    formatted_child_dob = format_dob(child['child_dob'])
    child_age = calculate_age(child['child_dob'])
    child_stage = get_child_stage(child['child_dob'])     

    return render_template(
        "child_profile.html",
        child=child,
        formatted_child_dob=formatted_child_dob,
        child_age=child_age,
        child_stage=child_stage)

# Edit child 
@app.route('/edit_child', methods=['GET', 'POST'])
@login_required
def edit_child():
    user_id = session.get("user_id")

    conn = get_db_connection()
    child = conn.execute(
        "SELECT * FROM children WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if request.method == "POST":
        if 'cancel' in request.form:
            flash("Update cancelled.")
            return redirect('/child')

        name = request.form.get("child_name")
        dob = request.form.get("child_dob")
        gender = request.form.get("child_gender")

        if child:
            conn.execute("""
                UPDATE children
                SET child_name = ?, child_dob = ?, child_gender = ?
                WHERE user_id = ?
            """, (name, dob, gender, user_id))
        else:
            conn.execute("""
                INSERT INTO children (user_id, child_name, child_dob, child_gender, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (user_id, name, dob, gender))

        conn.commit()
        conn.close()

        flash("Child profile updated.")
        return redirect(url_for('child_profile'))

    conn.close()
    return render_template("edit_child.html", child=child)

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    first_name = session.get('first_name')
    greeting = get_greeting()

    conn = get_db_connection()
    child = conn.execute(
        "SELECT * FROM children WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()


    today = date.today()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)

    # Fetch today's logs 
    feeds = list(db.feeding_logs.find({
        "user_id": user_id,
        "time": {"$gte": today_start, "$lte": today_end}
    }))

    total_meals = db.feeding_logs.count_documents({
    "user_id": user_id,
    "type": "Meal",
    "time": {"$gte": today_start, "$lte": today_end}
    })

    total_snacks = db.feeding_logs.count_documents({
    "user_id": user_id,
    "type": "Snack",
    "time": {"$gte": today_start, "$lte": today_end}
    })

    total_drank = db.feeding_logs.count_documents({
    "user_id": user_id,
    "type": {"$in": ["Milk", "Water", "Juice"]},
    "time": {"$gte": today_start, "$lte": today_end}
    })

    
    sleeps = list(db.sleep_logs.find({
        "user_id": user_id,
        "time": {"$gte": today_start, "$lte": today_end}
    }))

    total_naps = sleep_logs.count_documents({
        "user_id": user_id,
        "start_time": {"$gte": today_start, "$lte": today_end}    
    })
    
    total_sleep_minutes = sum(
        (s["end_time"] - s["start_time"]).total_seconds() / 60
        for s in sleeps
    )

    sleep_hours = total_sleep_minutes // 60
    sleep_minutes = total_sleep_minutes % 60
    total_sleep_formatted = f"{sleep_hours}h {sleep_minutes}m"

    nappies = list(db.nappy_logs.find({
        "user_id": user_id,
        "time": {"$gte": today_start, "$lte": today_end}
    }))
    
    total_nappies = len(nappies)
    wet_count = sum(1 for n in nappies if n["nappy_type"] == "Wet")
    dirty_count = sum(1 for n in nappies if n["nappy_type"] == "Dirty")

    return render_template(
        "dashboard.html",
        feeds=feeds,
        sleeps=sleeps,
        nappies=nappies,
        first_name=first_name,
        greeting=greeting, 
        total_meals=total_meals,
        total_snacks=total_snacks,
        total_drank=total_drank,
        total_nappies=total_nappies,
        wet_count=wet_count,
        dirty_count=dirty_count,
        total_sleep_minutes=total_sleep_minutes,
        total_naps=total_naps,
        total_sleep_formatted=total_sleep_formatted,
        child=child
)

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
            "user_id": session['user_id'],
            "time": time_dt,
            "type": feed_type,
            "amount": amount,
            "unit": unit,
            "notes": notes,
        })

        return redirect(url_for('feeding'))
   
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
           "user_id": session['user_id'],            
            "start_time": start,
            "end_time": end,
            "duration": duration_str,
            "notes": notes 
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
            "nappy_type": nappy_type,
            "notes": notes,
        })

    logs = list(
        db.nappy_logs
        .find({"user_id": session['user_id']})
        .sort("_id", -1)
    )

    return render_template('nappy.html', logs=logs)

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
            "nappy_type": nappy_type,
            "notes": notes,
            }}
        )

        flash("Nappy entry updated.")
        return redirect ('/nappy')
    

    return render_template ('edit_nappy.html', log=log)

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

def open_browser():
    webbrowser.open_new('http://localhost:5000/')

def app_run_flask():
     Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
     app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

app_run_flask() 

