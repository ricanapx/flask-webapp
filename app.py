from flask import Flask # Import the Flask library to create a web application

app = Flask(__name__) # Create an instance of the Flask class, which will be our WSGI application

@app.route('/') # Define a route for the root URL ("/") and associate it with the home function
def home():  # Define a function that will be called when the root URL is accessed.
    return 'Hello, World!' # Return a simple string "Hello, World!" as the response when the root URL is accessed.

# Running the app witha custom host and port, enabling debug mode, and disabling the reloader to prevent the server from restarting automatically when code changes are detected. This is useful for development purposes.
if __name__ == '__main__': 

    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False) 

