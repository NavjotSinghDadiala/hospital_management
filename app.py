from flask import Flask, render_template, request, redirect, url_for, session
from extensions import db
from models import User, Patient, Doctor

app = Flask(__name__)
app.secret_key = "abc-secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        age = request.form["age"]
        gender = request.form["gender"]
        contact = request.form["contact"]

        new_user = User(username=username, password=password, role="patient")
        db.session.add(new_user)
        db.session.commit()

        patient = Patient(user_id=new_user.id, age=age, gender=gender, contact=contact)
        db.session.add(patient)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session["user"] = user.username
            session["role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin"))

            if user.role == "doctor":
                return redirect(url_for("doctor_dashboard"))

            if user.role == "patient":
                return redirect(url_for("patient_dashboard"))

        return "Invalid Login"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    doctors = Doctor.query.count()
    patients = Patient.query.count()

    return render_template("admin_dashboard.html",
                           doctors=doctors,
                           patients=patients)


# ---------------- DOCTOR DASHBOARD ----------------

@app.route("/doctor_dashboard")
def doctor_dashboard():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    doctor = Doctor.query.filter_by(user_id=user.id).first()

    return render_template("doctor_dashboard.html", doctor=doctor)


# ---------------- PATIENT DASHBOARD ----------------

@app.route("/patient_dashboard")
def patient_dashboard():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    patient = Patient.query.filter_by(user_id=user.id).first()

    return render_template("patient_dashboard.html", patient=patient)



if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # create admin only once
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin", role="admin")
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
