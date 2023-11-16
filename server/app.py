from flask import Flask

app= Flask(__name__)

@app.route('/')
def root():
    return '<html><body>Hello World!</body></html>'

if __name__ == '__main__':
    app.run(debug=True, port='5555')
