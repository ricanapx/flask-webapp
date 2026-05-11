import webbrowser
import sqlite3 
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for 

app = Flask(__name__) 

users = []  # A list to store user data (for demonstration purposes)

# Open the default web browser and navigate to the specified URL (http://localhost:5000/)
 

# Database Connection
def get_db_connections():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# CREATE USERS TABLE
def create_users_table():
    conn = get_db_connections()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )         
    ''')
    conn.commit()
    conn.close()

# CREATE CHILDCARE TABLES
def create_chilcare_tables():
    conn = get_db_connections()

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
            type TEXT NOT NULL,
            notes TEXT 
        )
    ''')

    conn.commit()
    conn.close()

# Run table creation
create_users_table()
create_chilcare_tables()

#ROUTES  
@app.route('/') 
def home():  
    return render_template('home.html')  # Render the home.html template and pass the users list to it

@app.route('/about')
def about():
    return render_template('about.html')  # Render the about.html template

# REGISTER USER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':  
        name = request.form['name']  
        email = request.form['email'] 
        
        conn = get_db_connections()
        conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
        conn.close()

        return redirect(url_for('home'))  # Redirect to the home page after registration
    
    return render_template('register.html')  # Render the register.html template for GET requests

# VIEW USERS
@app.route('/data')
def data(): 
    conn = get_db_connections()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('data.html', users=users)  # Render the data.html template and pass the users list to it

@app.route('/contact')
def contact():
    return render_template('contact.html')  # Render the contact.html template

# FEEDING ROUTE
@app.route('/feeding', methods=['GET', 'POST'])
def feeding():
    conn = get_db_connections()

    if request.method == 'POST':
        time = request.form['time']
        amount = request.form['amount']
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
def sleep():
    conn = get_db_connections()

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
def nappy():
    conn = get_db_connections()

    if request.method == 'POST':
        time = request.form['time']
        type = request.form['type']
        notes = request.form['notes']

        conn.execute("INSERT INTO nappy (time, type, notes) VALUES (?, ?, ?)",
                     (time, type, notes))
        conn.commit()
    logs = conn.execute("SELECT * FROM nappy ORDER BY id DESC").fetchall()
    conn.close()

    return render_template('nappy.html', logs=logs)


# RUN FLASK 
def open_browser():
    webbrowser.open_new('http://localhost:5000/')

def app_run_flask():
     Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
     app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

# Running the app with a custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes
app_run_flask() 

