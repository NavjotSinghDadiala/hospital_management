from flask import Flask, render_template, request, redirect, url_for, session
from extensions import db
from models import *

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

@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        name = request.form["name"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]

        if User.query.filter_by(username=username).first():
            return "Username already taken. Pick another."
        new_user = User(username=username, password=password, role="doctor")
        db.session.add(new_user)
        db.session.commit()

        doctor = Doctor(user_id=new_user.id, name=name,
                        specialization=specialization, experience=experience)
        db.session.add(doctor)
        db.session.commit()

        return redirect(url_for("view_doctors"))
    return render_template("add_doctor.html")




@app.route("/book_appointment/<int:doctor_id>", methods=["GET", "POST"])
def book_appointment(doctor_id):
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    patient = Patient.query.filter_by(user_id=user.id).first()
    doctor = Doctor.query.filter_by(id=doctor_id).first()
    avails = Availability.query.filter_by(doctor_id=doctor_id).all()
    if request.method == "POST":
        date = request.form["date"]
        time = request.form["time"]
        exists = Appointment.query.filter_by(doctor_id=doctor_id, date=date, time=time, status="booked").first()
        if exists:
            return "Slot already booked"
        a = Appointment(patient_id=patient.id, doctor_id=doctor_id, date=date, time=time, status="booked")
        db.session.add(a)
        db.session.commit()
        return redirect(url_for("my_appointments"))
    return render_template("book_appointment.html", doctor=doctor, avails=avails)

@app.route("/my_appointments")
def my_appointments():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    patient = Patient.query.filter_by(user_id=user.id).first()
    appts = Appointment.query.filter_by(patient_id=patient.id).all()
    doctors = {d.id: d for d in Doctor.query.all()}
    return render_template("my_appointments.html", appts=appts, doctors=doctors)

@app.route("/cancel_appointment/<int:appt_id>")
def cancel_appointment(appt_id):
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    a = Appointment.query.filter_by(id=appt_id, status="booked").first()
    if a:
        a.status = "cancelled"
        db.session.commit()
    return redirect(url_for("my_appointments"))

@app.route("/doctor_appointments")
def doctor_appointments():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    doc = Doctor.query.filter_by(user_id=user.id).first()
    appts = Appointment.query.filter_by(doctor_id=doc.id).all()
    patients = {p.id: p for p in Patient.query.all()}
    return render_template("doctor_appointments.html", appts=appts, patients=patients)

@app.route("/mark_completed/<int:appt_id>", methods=["POST"])
def mark_completed(appt_id):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))
    a = Appointment.query.filter_by(id=appt_id).first()
    if a:
        a.status = "completed"
        db.session.commit()
    return redirect(url_for("doctor_appointments"))


# ---------------- DOCTOR DASHBOARD ----------------

@app.route("/doctor_dashboard")
def doctor_dashboard():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    avails = Availability.query.filter_by(doctor_id=doctor.id).all()

    return render_template("doctor_dashboard.html", doctor=doctor , avails=avails)

@app.route("/view_doctors", methods=["GET", "POST"])
def view_doctors():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        doc_id = request.form["doc_id"]
        name = request.form["name"]
        specialization = request.form["specialization"]
        experience = request.form["experience"]

        d = Doctor.query.filter_by(id=doc_id).first()
        if d:
            d.name = name
            d.specialization = specialization
            d.experience = experience
            db.session.commit()

        return redirect("/view_doctors")

    doctor_list = Doctor.query.all()
    doctors_with_user = []
    for d in doctor_list:
        u = User.query.filter_by(id=d.user_id).first()
        doctors_with_user.append((d, u))

    return render_template("view_doctors.html", doctors=doctors_with_user)

@app.route("/delete_doctor/<int:doc_id>")
def delete_doctor(doc_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    d = Doctor.query.filter_by(id=doc_id).first()
    if d:
        u = User.query.filter_by(id=d.user_id).first()
        db.session.delete(d)
        if u:
            db.session.delete(u)
        db.session.commit()

    return redirect("/view_doctors")

@app.route("/search_doctors", methods=["GET", "POST"])
def search_doctors():
    if "role" not in session:
        return redirect(url_for("login"))
    doctors = []
    q = ""
    if request.method == "POST":
        q = request.form.get("q", "").strip()
        doctors = Doctor.query.filter(Doctor.name.contains(q) | Doctor.specialization.contains(q)).all()
    return render_template("search_doctors.html", doctors=doctors, q=q)

@app.route("/view_doctor/<int:doctor_id>")
def view_doctor(doctor_id):
    if "role" not in session:
        return redirect(url_for("login"))
    doctor = Doctor.query.filter_by(id=doctor_id).first()
    avails = Availability.query.filter_by(doctor_id=doctor_id).all()
    return render_template("view_doctor.html", doctor=doctor, avails=avails)

@app.route("/add_availability", methods=["GET", "POST"])
def add_availability():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    doc = Doctor.query.filter_by(user_id=user.id).first()

    slots = [
        "09:00-10:00",
        "10:00-11:00",
        "11:00-12:00",
        "12:00-13:00",
        "14:00-15:00",
        "15:00-16:00",
        "16:00-17:00"
    ]

    if request.method == "POST":
        date = request.form["date"]
        slot = request.form["slot"]
        av = Availability(doctor_id=doc.id, date=date, slot=slot)
        db.session.add(av)
        db.session.commit()
        return redirect(url_for("doctor_dashboard"))
    return render_template("add_availability.html" , slots=slots)

@app.route("/delete_availability/<int:aid>")
def delete_availability(aid):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    a = Availability.query.filter_by(id=aid).first()
    if a:
        db.session.delete(a)
        db.session.commit()

    return redirect("/doctor_dashboard")






# ---------------- PATIENT DASHBOARD ----------------

@app.route("/patient_dashboard")
def patient_dashboard():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    patient = Patient.query.filter_by(user_id=user.id).first()

    return render_template("patient_dashboard.html", patient=patient)

@app.route("/view_patients")
def view_patients():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    users = User.query.filter_by(role="patient").all()
    pts = []

    for u in users:
        p = Patient.query.filter_by(user_id=u.id).first()
        pts.append((u, p))

    return render_template("view_patients.html", patients=pts)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # create admin only once
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin", role="admin")
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
