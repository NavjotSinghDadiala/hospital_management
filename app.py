from flask import Flask, render_template, request, redirect, url_for, session
from extensions import db
from models import *
from datetime import datetime , timedelta

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
        fullname = request.form["fullname"]
        age = request.form["age"]
        gender = request.form["gender"]
        contact = request.form["contact"]

        new_user = User(username=username, password=password, role="patient")
        db.session.add(new_user)
        db.session.commit()

        patient = Patient(user_id=new_user.id, name=fullname, age=age, gender=gender, contact=contact)
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
            if not user.is_valid:
                return "Your account is not approved yet. Contact admin."
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

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    q = ""
    doctor_results = []
    patient_results = []

    if request.method == "POST":
        q = request.form["q"]

        doctor_list = Doctor.query.filter(
            Doctor.name.contains(q) | Doctor.specialization.contains(q)
        ).all()
        
        for d in doctor_list:
            u = User.query.filter_by(id=d.user_id).first()
            if u:
                doctor_results.append((d, u))
        users = User.query.filter(User.username.contains(q), User.role == "patient").all()
        try:
            patient_id = int(q)
            p_by_id = Patient.query.filter_by(id=patient_id).first()
            if p_by_id:
                u_by_id = User.query.filter_by(id=p_by_id.user_id).first()
                if u_by_id and (u_by_id, p_by_id) not in [(u, p) for u, p in patient_results]:
                    users.append(u_by_id)
        except:
            pass
        
        patients_by_contact = Patient.query.filter(Patient.contact.contains(q)).all()
        for p_contact in patients_by_contact:
            u_contact = User.query.filter_by(id=p_contact.user_id).first()
            if u_contact and u_contact.role == "patient":
                if (u_contact, p_contact) not in [(u, p) for u, p in patient_results]:
                    users.append(u_contact)
        
        for u in users:
            p = Patient.query.filter_by(user_id=u.id).first()
            if p:
                patient_results.append((u, p))

    doctors = Doctor.query.all()
    patients = Patient.query.all()
    appointments = Appointment.query.all()

    return render_template("admin_dashboard.html",q=q,doctors=doctors,patients=patients,appointments=appointments,doctor_results=doctor_results,patient_results=patient_results)


@app.route("/blacklist/<int:uid>")
def blacklist(uid):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    u = User.query.filter_by(id=uid).first()
    if u:
        u.is_valid = False
        db.session.commit()

    return redirect("/admin")

@app.route("/unblacklist/<int:uid>")
def unblacklist(uid):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    u = User.query.filter_by(id=uid).first()
    if u:
        u.is_valid = True
        db.session.commit()
    return redirect("/admin")

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
    if not user:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "Patient profile not found. Please contact admin."
    doctor = Doctor.query.filter_by(id=doctor_id).first()
    if not doctor:
        return "Doctor not found."

    all_avails = Availability.query.filter_by(doctor_id=doctor_id).all()
    
    avails = []
    for avail in all_avails:
        booked = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=avail.date,
            time=avail.slot,
            status="booked"
        ).first()
        if not booked:
            avails.append(avail)

    error = ""

    if request.method == "POST":
        slot = request.form["slot"]

        parts = slot.split(" | ")
        date = parts[0]
        time = parts[1]

        exists = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date,
            time=time,
            status="booked"
        ).first()

        if exists:
            error = "Slot already booked"
            return render_template("book_appointment.html", doctor=doctor, avails=avails, error=error)

        a = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            date=date,
            time=time,
            status="booked"
        )

        db.session.add(a)
        db.session.commit()
        return redirect("/my_appointments")

    return render_template("book_appointment.html", doctor=doctor, avails=avails, error=error)


@app.route("/my_appointments")
def my_appointments():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "Patient profile not found. Please contact admin."
    
    
    
    all_appts = Appointment.query.filter_by(patient_id=patient.id).all()
    doctors = {d.id: d for d in Doctor.query.all()}
    
    today = datetime.now().date()
    upcoming_appts = []
    past_appts = []
    
    for a in all_appts:
        try:
            appt_date = datetime.strptime(a.date, "%Y-%m-%d").date()
            if a.status == "booked" and appt_date >= today:
                upcoming_appts.append(a)
            else:
                past_appts.append(a)
        except:
            past_appts.append(a)
    
    return render_template("my_appointments.html", 
                         upcoming_appts=upcoming_appts, 
                         past_appts=past_appts, 
                         doctors=doctors)


@app.route("/doctor_appointments")
def doctor_appointments():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    doc = Doctor.query.filter_by(user_id=user.id).first()
    if not doc:
        return "Doctor profile not found. Please contact admin."
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

@app.route("/view_appointments")
def view_appointments():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    today = datetime.now().date()
    appts = Appointment.query.all()
    upcoming_list = []
    past_list = []
    for a in appts:
        p = Patient.query.filter_by(id=a.patient_id).first()
        d = Doctor.query.filter_by(id=a.doctor_id).first()
        if p and d:
            pu = User.query.filter_by(id=p.user_id).first()
            du = User.query.filter_by(id=d.user_id).first()
            if pu and du:
                try:
                    appt_date = datetime.strptime(a.date, "%Y-%m-%d").date()
                    if a.status == "booked" and appt_date >= today:
                        upcoming_list.append((a, p, pu, d, du))
                    else:
                        past_list.append((a, p, pu, d, du))
                except:
                    past_list.append((a, p, pu, d, du))
    return render_template("view_appointments.html", upcoming_list=upcoming_list, past_list=past_list)





# ---------------- DOCTOR DASHBOARD ----------------

@app.route("/doctor_dashboard")
def doctor_dashboard():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    if not doctor:
        return "Doctor profile not found. Please contact admin."
    
    all_avails = Availability.query.filter_by(doctor_id=doctor.id).all()
    avails = []
    for avail in all_avails:
        booked = Appointment.query.filter_by(
            doctor_id=doctor.id,
            date=avail.date,
            time=avail.slot,
            status="booked"
        ).first()
        if not booked:
            avails.append(avail)
    
    today = datetime.now().date()
    week_later = today + timedelta(days=7)
    all_appts = Appointment.query.filter_by(doctor_id=doctor.id).all()
    upcoming_appts = []
    all_patients_list = []
    patient_ids_seen = []
    for a in all_appts:
        p = Patient.query.filter_by(id=a.patient_id).first()
        if p:
            u = User.query.filter_by(id=p.user_id).first()
            if u:
                if a.patient_id not in patient_ids_seen:
                    all_patients_list.append((u, p))
                    patient_ids_seen.append(a.patient_id)
                try:
                    appt_date = datetime.strptime(a.date, "%Y-%m-%d").date()
                    if a.status == "booked" and appt_date >= today and appt_date <= week_later:
                        upcoming_appts.append((a, p, u))
                except:
                    pass
    return render_template(
        "doctor_dashboard.html",doctor=doctor,avails=avails,full_list=upcoming_appts,patients_count=len(all_patients_list),appointments_count=len(upcoming_appts)
    )


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

    q = ""
    doctors = Doctor.query.all()

    if request.method == "POST":
        q = request.form.get("q", "").strip()
        doctors = Doctor.query.filter(
            Doctor.name.contains(q) | Doctor.specialization.contains(q)
        ).all()

    return render_template("search_doctors.html", doctors=doctors, q=q)


@app.route("/view_doctor/<int:doctor_id>")
def view_doctor(doctor_id):
    if "role" not in session:
        return redirect(url_for("login"))

    doctor = Doctor.query.filter_by(id=doctor_id).first()
    if not doctor:
        return "Doctor not found."
    
    all_avails = Availability.query.filter_by(doctor_id=doctor_id).all()
    
    avails = []
    for avail in all_avails:
        booked = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=avail.date,
            time=avail.slot,
            status="booked"
        ).first()
        if not booked:
            avails.append(avail)

    return render_template("view_doctor.html", doctor=doctor, avails=avails)


@app.route("/add_availability", methods=["GET", "POST"])
def add_availability():
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    doc = Doctor.query.filter_by(user_id=user.id).first()
    if not doc:
        return "Doctor profile not found. Please contact admin."


    
    slots = [
        "09:00-10:00",
        "10:00-11:00",
        "11:00-12:00",
        "12:00-13:00",
        "14:00-15:00",
        "15:00-16:00",
        "16:00-17:00"
    ]
    
    today = datetime.now().date()
    max_date = today + timedelta(days=7)
    min_date_str = today.strftime("%Y-%m-%d")
    max_date_str = max_date.strftime("%Y-%m-%d")

    error = ""

    if request.method == "POST":
        date = request.form["date"]
        slot = request.form["slot"]
        
        try:
            selected_date = datetime.strptime(date, "%Y-%m-%d").date()
            if selected_date < today or selected_date > max_date:
                error = "Date must be within the next 7 days from today."
                return render_template("add_availability.html", slots=slots, error=error, min_date=min_date_str, max_date=max_date_str)
        except:
            error = "Invalid date format."
            return render_template("add_availability.html", slots=slots, error=error, min_date=min_date_str, max_date=max_date_str)

        exists = Availability.query.filter_by(doctor_id=doc.id, date=date, slot=slot).first()
        if exists:
            error = "This slot already exists"
            return render_template("add_availability.html", slots=slots, error=error, min_date=min_date_str, max_date=max_date_str)

        a = Availability(doctor_id=doc.id, date=date, slot=slot)
        db.session.add(a)
        db.session.commit()
        return redirect("/doctor_dashboard")

    return render_template("add_availability.html", slots=slots, error=error, min_date=min_date_str, max_date=max_date_str)


@app.route("/delete_availability/<int:aid>")
def delete_availability(aid):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    a = Availability.query.filter_by(id=aid).first()
    if a:
        db.session.delete(a)
        db.session.commit()

    return redirect("/doctor_dashboard")

@app.route("/complete_appointment/<int:aid>")
def complete_appointment(aid):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    a = Appointment.query.filter_by(id=aid).first()
    if a and a.status == "booked":
        a.status = "completed"
        db.session.commit()

    return redirect("/doctor_dashboard")

@app.route("/cancel_appointment/<int:aid>")
def cancel_appointment(aid):
    if "role" not in session:
        return redirect("/login")

    a = Appointment.query.filter_by(id=aid).first()
    if not a:
        return redirect("/login")

    if session["role"] == "patient":
        if a.status == "booked":
            a.status = "cancelled"
            db.session.commit()
        return redirect("/my_appointments")

    if session["role"] == "doctor":
        a.status = "cancelled"
        db.session.commit()
        return redirect("/doctor_dashboard")

    return redirect("/login")


@app.route("/doctor_patients")
def doctor_patients():
    if "role" not in session or session["role"] != "doctor":
        return redirect("/login")

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    if not doctor:
        return "Doctor profile not found. Please contact admin."

    apps = Appointment.query.filter_by(doctor_id=doctor.id).all()

    p_ids = []
    for a in apps:
        if a.patient_id not in p_ids:
            p_ids.append(a.patient_id)

    patients = []
    for pid in p_ids:
        p = Patient.query.filter_by(id=pid).first()
        u = User.query.filter_by(id=p.user_id).first()
        # find the most recent completed appointment for this patient (with this doctor)
        appts_for_patient = Appointment.query.filter_by(patient_id=pid, doctor_id=doctor.id).all()
        # sort appointments by date desc (best-effort) and pick first completed without treatment
        try:
            appts_for_patient.sort(key=lambda x: datetime.strptime(x.date, "%Y-%m-%d") if x.date else datetime.min, reverse=True)
        except:
            pass

        add_treatment_aid = None
        for a in appts_for_patient:
            if a.status == 'completed':
                t = Treatment.query.filter_by(appointment_id=a.id).first()
                if not t:
                    add_treatment_aid = a.id
                    break

        patients.append((u, p, add_treatment_aid))

    return render_template("doctor_patients.html", patients=patients)

@app.route("/doctor_patient_history/<int:patient_id>")
def doctor_patient_history(patient_id):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    if not doctor:
        return "Doctor profile not found. Please contact admin."
    
    patient = Patient.query.filter_by(id=patient_id).first()
    if not patient:
        return "Patient not found."
    
    patient_user = User.query.filter_by(id=patient.user_id).first()
    if not patient_user:
        return "Patient user not found."
    
    appts = Appointment.query.filter_by(patient_id=patient_id, doctor_id=doctor.id).all()
    
    full_history = []
    
    for a in appts:
        t = Treatment.query.filter_by(appointment_id=a.id).first()
        full_history.append((a, t))
    
    try:
        full_history.sort(key=lambda x: datetime.strptime(x[0].date, "%Y-%m-%d") if x[0].date else datetime.min, reverse=True)
    except:
        pass
    
    return render_template("doctor_patient_history.html", patient=patient, patient_user=patient_user,doctor=doctor,full_history=full_history)




# ---------------- PATIENT DASHBOARD ----------------

@app.route("/patient_dashboard")
def patient_dashboard():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "Patient profile not found. Please contact admin."
    
    today = datetime.now().date()
    week_later = today + timedelta(days=7)
    
    all_doctors = Doctor.query.all()
    specializations = []
    for d in all_doctors:
        if d.specialization and d.specialization not in specializations:
            specializations.append(d.specialization)
    
    doctors_with_availability = []
    for d in all_doctors:
        avails = Availability.query.filter_by(doctor_id=d.id).all()
        has_upcoming_availability = False
        for avail in avails:
            try:
                avail_date = datetime.strptime(avail.date, "%Y-%m-%d").date()
                if avail_date >= today and avail_date <= week_later:
                    booked = Appointment.query.filter_by(
                        doctor_id=d.id,
                        date=avail.date,
                        time=avail.slot,
                        status="booked"
                    ).first()
                    if not booked:
                        has_upcoming_availability = True
                        break
            except:
                pass
        if has_upcoming_availability:
            doctors_with_availability.append(d)
    
    appts = Appointment.query.filter_by(patient_id=patient.id).all()
    upcoming_appts = []
    past_appts = []
    for a in appts:
        try:
            appt_date = datetime.strptime(a.date, "%Y-%m-%d").date()
            if a.status == "booked" and appt_date >= today:
                upcoming_appts.append(a)
            else:
                past_appts.append(a)
        except:
            past_appts.append(a)
    return render_template("patient_dashboard.html", 
                          patient=patient,
                          specializations=specializations,
                          doctors_count=len(doctors_with_availability),
                          upcoming_count=len(upcoming_appts),
                          past_count=len(past_appts))

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

@app.route("/view_patient/<int:user_id>")
def view_patient(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return "Patient not found."
    
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return "Patient profile not found."
    
    return render_template("view_patient.html", user=user, patient=patient)

@app.route("/edit_my_profile", methods=["GET", "POST"])
def edit_my_profile():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "Patient profile not found. Please contact admin."
    
    if request.method == "POST":
        age = request.form.get("age", "")
        gender = request.form.get("gender", "")
        contact = request.form.get("contact", "")
        
        if age:
            patient.age = age
        if gender:
            patient.gender = gender
        if contact:
            patient.contact = contact
        
        db.session.commit()
        return redirect("/patient_dashboard")
    
    return render_template("edit_my_profile.html", user=user, patient=patient)

@app.route("/edit_patient/<int:user_id>", methods=["GET", "POST"])
def edit_patient(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return "Patient not found."
    
    patient = Patient.query.filter_by(user_id=user_id).first()
    if not patient:
        return "Patient profile not found."
    
    if request.method == "POST":
        age = request.form.get("age", "")
        gender = request.form.get("gender", "")
        contact = request.form.get("contact", "")
        
        if age:
            patient.age = age
        if gender:
            patient.gender = gender
        if contact:
            patient.contact = contact
        
        db.session.commit()
        return redirect("/view_patients")
    
    return render_template("edit_patient.html", user=user, patient=patient)

@app.route("/delete_patient/<int:user_id>")
def delete_patient(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    
    user = User.query.filter_by(id=user_id).first()
    if user and user.role == "patient":
        patient = Patient.query.filter_by(user_id=user_id).first()
        if patient:
            db.session.delete(patient)
        db.session.delete(user)
        db.session.commit()
    
    return redirect("/view_patients")

@app.route("/add_treatment/<int:aid>", methods=["GET", "POST"])
def add_treatment(aid):
    if "role" not in session or session["role"] != "doctor":
        return redirect(url_for("login"))

    a = Appointment.query.filter_by(id=aid).first()
    if not a:
        return "Appointment not found."

    existing_t = Treatment.query.filter_by(appointment_id=aid).first()
    if existing_t:
        return redirect(url_for("doctor_patient_history", patient_id=a.patient_id))

    if request.method == "POST":
        diagnosis = request.form["diagnosis"]
        prescription = request.form["prescription"]
        notes = request.form["notes"]

        t = Treatment(appointment_id=aid, diagnosis=diagnosis, prescription=prescription, notes=notes)
        db.session.add(t)
        db.session.commit()

        return redirect("/doctor_dashboard")

    return render_template("add_treatment.html", appointment=a)

@app.route("/treatment_history")
def treatment_history():
    if "role" not in session or session["role"] != "patient":
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["user"]).first()
    if not user:
        return redirect(url_for("login"))
    patient = Patient.query.filter_by(user_id=user.id).first()
    if not patient:
        return "Patient profile not found. Please contact admin."

    appts = Appointment.query.filter_by(patient_id=patient.id, status="completed").all()

    full_list = []
    for a in appts:
        t = Treatment.query.filter_by(appointment_id=a.id).first()
        d = Doctor.query.filter_by(id=a.doctor_id).first()
        u = User.query.filter_by(id=d.user_id).first()
        full_list.append((a, t, d, u))

    return render_template("treatment_history.html", full_list=full_list)












if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin", role="admin")
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)
