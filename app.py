import flask # Import the Flask library to create a web application

app = flask.Flask(__name__) # Create an instance of the Flask class, which will be our WSGI application

@app.route('/') # Define a route for the root URL ("/") and associate it with the hello_world function

def hello_world():  # Define a function that will be called when the root URL is accessed. This function returns a simple string "Hello, World!" as the response to the client. 
    return 'Hello, World!'
if __name__ == '__main__': # Check if the script is being run directly (as the main program) and not imported as a module. If this condition is true, the code inside this block will be executed.

    app.run(debug=True, host='<IP_ADDRESS>', port=5000) # Start the Flask development server with debugging enabled, listening on all available network interfaces (
    
