import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for 

app = Flask(__name__) 

users = []  # A list to store user data (for demonstration purposes)

# Open the default web browser and navigate to the specified URL (http://localhost:5000/)
def open_browser():
    webbrowser.open_new('http://localhost:5000/') 

# Route for the home page 
@app.route('/') 
def home():  
    return render_template('home.html')  # Render the home.html template and pass the users list to it

@app.route('/about')
def about():
    return render_template('about.html')  # Render the about.html template

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':  # Check if the request method is POST (form submission)
        name = request.form['name']  # Get the name from the form data
        email = request.form['email']  # Get the email from the form data
        users.append({'name': name, 'email': email})  # Add the user data to the users list
        return redirect(url_for('home'))  # Redirect to the home page after registration
    return render_template('register.html')  # Render the register.html template for GET requests

@app.route('/data')
def data(): 
    return render_template('data.html')  # Render the data.html template and pass the users list to it

@app.route('/contact')
def contact():
    return render_template('contact.html')  # Render the contact.html template

# Function to run the Flask application.
def app_run():
     Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
     app.run(host='0.0.0', port=5000, debug=True, use_reloader=False)

# Running the app with a custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes
app_run() 




