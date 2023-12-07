from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='../client')

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'app.html')

# If you have other static files like CSS, JS, images, etc., you can serve them using a separate route.
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(debug=True, port=5555)
