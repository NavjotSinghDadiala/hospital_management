from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    contact = db.Column(db.String(50))

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100))
    specialization = db.Column(db.String(100))
    experience = db.Column(db.String(100))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, nullable=False)
    doctor_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    status = db.Column(db.String(20))

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, nullable=False)
    diagnosis = db.Column(db.String(500))
    prescription = db.Column(db.String(500))
    notes = db.Column(db.String(500))

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20))
    slot = db.Column(db.String(20))

class Treatment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, nullable=False)
    diagnosis = db.Column(db.String(200))
    prescription = db.Column(db.String(200))
    notes = db.Column(db.String(300))
