import webbrowser
from threading import Timer
from flask import Flask 

app = Flask(__name__) 

# Open the default web browser and navigate to the specified URL (http://localhost:5000/)
def open_browser():
    webbrowser.open_new('http://localhost:5000/') 

# Route for the home page 
@app.route('/') 
def home():  
    return '''
    <html>
        <head>
            <title>Flask App</title>
        </head>
        <body>
            <h1>Welcome to the Flask App!</h1>
            <p>This is a simple Flask application running on localhost.</p>
        </body> 
    </html>
    '''

@app.route('/about')
def about():
    return '''
    <html>
        <head>
            <title>About Flask App</title>
        </head>
        <body>
            <h1>About This Flask App</h1>
            <p>This page is a an example to demonstrate flask routing.</p>
        </body>
    </html>
    '''
# Running the app with a custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes.
if __name__ == '__main__': 
    Timer(1, open_browser).start() # Start a timer that will call the open_browser function after 1 second, which will open the web browser to the specified URL.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False) 




