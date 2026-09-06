from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/tasks")
def tasks():
    return render_template("tasks.html")

@app.route("/calendar")
def calendar():
    return ("calendar page not available")

if __name__ == "__main__":
    app.run(debug=True)