from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import psycopg2
import urllib.parse

web = Flask(__name__)
web.secret_key = '12345'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
web.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Parse the DATABASE_URL to components
    result = urllib.parse.urlparse(DATABASE_URL)
    db = psycopg2.connect(
        dbname=result.path[1:],  # skip leading '/'
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
else:
    # Fallback for local development
    db = psycopg2.connect(
        host="localhost",
        user="postgre",
        password="2004",
        dbname="enrollment_db"
    )

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_last_insert_id(cursor, table_name, id_column):
    cursor.execute(f"SELECT currval(pg_get_serial_sequence('{table_name}', '{id_column}'))")
    return cursor.fetchone()[0]

@web.route('/')
def home():
    return render_template('index.html')

@web.route('/form')
def form():
    return render_template('personaldetails.html')

@web.route('/submit', methods=['POST'])
def submit_form():
    session['personal_data'] = {
        'first_name': request.form.get('first_name'),
        'last_name': request.form.get('last_name'),
        'middle_name': request.form.get('middle_name'),
        'address': request.form.get('address'),
        'contact': request.form.get('contact'),
        'district': request.form.get('district'),
        'email': request.form.get('email'),
        'gender': request.form.get('gender'),
        'birthdate': request.form.get('birthdate'),
        'lrn': request.form.get('lrn'),
        'age': request.form.get('age'),
        'citizenship': request.form.get('citizenship'),
        'civil_status': request.form.get('civil_status'),
        'religion': request.form.get('religion'),
        'father_name': request.form.get('father_name'),
        'father_occupation': request.form.get('father_occupation'),
        'father_contact': request.form.get('father_contact'),
        'mother_name': request.form.get('mother_name'),
        'mother_occupation': request.form.get('mother_occupation'),
        'mother_contact': request.form.get('mother_contact'),
        'guardian_name': request.form.get('guardian_name'),
        'guardian_occupation': request.form.get('guardian_occupation'),
        'guardian_contact': request.form.get('guardian_contact')
    }
    return redirect(url_for('educational_background'))

# ------------------ Educational Background ------------------
@web.route('/educational', methods=['GET', 'POST'])
def educational_background():
    if request.method == 'POST':
        session['education'] = {
            'first_gen': request.form.get('first_gen'),
            'elementary': request.form.get('elementary'),
            'elem_year': request.form.get('elem_year'),
            'elem_honors': request.form.get('elem_honors'),
            'highschool': request.form.get('highschool'),
            'hs_year': request.form.get('hs_year'),
            'hs_honors': request.form.get('hs_honors'),
            'college': request.form.get('college'),
            'college_year': request.form.get('college_year'),
            'college_honors': request.form.get('college_honors')
        }
        return redirect(url_for('course_detail'))
    return render_template('educational_bg.html')

# ------------------ Course Details ------------------
@web.route('/course', methods=['GET', 'POST'])
def course_detail():
    if request.method == 'POST':
        session['course'] = {
            'id_number': request.form.get('id_number'),
            'year_level': request.form.get('year_level'),
            'enroll_status': request.form.get('enroll'),
            'student_status': request.form.get('student')
        }
        return redirect(url_for('upload_requirements'))
    return render_template('course-detail.html')

# ------------------ Upload Requirements ------------------
@web.route('/upload', methods=['GET', 'POST'])
def upload_requirements():
    if request.method == 'POST':
        uploaded_files = {}

        personal_data = session.get('personal_data')
        if not personal_data:
            return redirect(url_for('form'))

        last_name = personal_data['last_name']
        first_name = personal_data['first_name']

        expected_suffixes = {
            'medical_certificate': 'Medical',
            'grades': 'Grades',
            'org_fee': 'OrgFee'
        }

        for field, suffix in expected_suffixes.items():
            file = request.files.get(field)

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)

                expected_prefix = f"{last_name}_{first_name}_{suffix}"
                if not filename.startswith(expected_prefix):
                    return f"<p>Invalid file name for {field}. Must start with: {expected_prefix}</p>"

                save_path = os.path.join(web.config['UPLOAD_FOLDER'], filename)
                file.save(save_path)
                uploaded_files[field] = filename
            else:
                return f"<p>Invalid file or format for {field}. Allowed formats: PDF, JPG, PNG</p>"

        session['uploaded_files'] = uploaded_files
        return redirect(url_for('submission'))

    return render_template('upload_requirements.html')

@web.route('/submission')
def submission():
    return render_template(
        'submission.html',
        personal=session.get('personal_data', {}),
        education=session.get('education', {}),
        course=session.get('course', {}),
        uploaded_files=session.get('uploaded_files', {})
    )

# ------------------ to DB ------------------
@web.route('/finalize', methods=['POST'])
def finalize_enrollment():
    pd = session.get('personal_data')
    education = session.get('education')
    course = session.get('course')
    uploaded = session.get('uploaded_files')

    if not pd or not education or not course or not uploaded:
        return redirect(url_for('home'))

    # Insert into student table
    student_sql = """
        INSERT INTO student (FirstName, LastName, MiddleName, Address, LRN, Contact, Email, Gender, BirthDate, Age, Citizenship, CivilStatus)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    student_values = (
        pd['first_name'], pd['last_name'], pd['middle_name'], pd['address'],
        pd['lrn'], pd['contact'], pd['email'], pd['gender'],
        pd['birthdate'], pd['age'], pd['citizenship'], pd['civil_status']
    )
    cursor.execute(student_sql, student_values)
    db.commit()
    student_id = get_last_insert_id(cursor, 'student', 'studentid')

    # Insert into parent table
    parent_sql = """
        INSERT INTO parent (StudentId, FatherName, MotherName, GuardianName, Occupation, Contact)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(parent_sql, (
        student_id,
        pd['father_name'],
        pd['mother_name'],
        pd['guardian_name'],
        pd['guardian_occupation'],
        pd['guardian_contact']
    ))
    db.commit()

    # Insert into studentcourse
    course_sql = """
        INSERT INTO studentcourse (StudentId, IdNumber, YearLvl)
        VALUES (%s, %s, %s)
    """
    cursor.execute(course_sql, (
        student_id,
        course['id_number'],
        course['year_level']
    ))
    db.commit()

    # Insert into enrollment
    enroll_sql = """
        INSERT INTO enrollment (StudentId, EnrollmentStatus, StudentStatus)
        VALUES (%s, %s, %s)
    """
    cursor.execute(enroll_sql, (
        student_id,
        course['enroll_status'],
        course['student_status']
    ))
    db.commit()

    # Insert into edubackground
    edubackground_sql = """
        INSERT INTO edubackground (StudentId, first_gen, elementary, elem_year, elem_honors,
        highschool, hs_year, hs_honors, college, college_year, college_honors)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(edubackground_sql, (
        student_id,
        education['first_gen'], education['elementary'], education['elem_year'],
        education['elem_honors'], education['highschool'], education['hs_year'],
        education['hs_honors'], education['college'], education['college_year'],
        education['college_honors']
    ))
    db.commit()

    # Insert into requirements table
    requirements_sql = """
        INSERT INTO requirements (StudentId, medical_certificate, grades, org_fee)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(requirements_sql, (
        student_id,
        uploaded.get('medical_certificate'),
        uploaded.get('grades'),
        uploaded.get('org_fee')
    ))
    db.commit()

    session.clear()
    return "<h2>Enrollment Successful!</h2><p>Thank you for enrolling.</p>"

if __name__ == '__main__':
    web.run(debug=True)
