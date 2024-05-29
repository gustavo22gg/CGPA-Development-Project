from flask import Flask, request, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
import os
import logging

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

csrf = CSRFProtect(app)

@app.route('/')
def index():
    return render_template('index.html')

# @csrf.exempt
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    login_url = 'https://usis.bracu.ac.bd/academia/j_spring_security_check'
    dashboard_url = 'https://usis.bracu.ac.bd/academia/dashBoard/successHandler'
    grade_sheet_url = 'https://usis.bracu.ac.bd/academia/studentCourse/loadPreviousResultByStudent?417&4170.8781830145818899&417'
    advised = 'https://usis.bracu.ac.bd/academia/studentCourse/advisedCourse?516&5160.8336748080926546&516'

    payload = {'j_username': username, 'j_password': password}

    with requests.Session() as session:
        login_response = session.post(login_url, data=payload)

        if login_response.status_code == 200:
            dashboard_response = session.get(dashboard_url)

            if dashboard_response.status_code == 200:
                grade_sheet_response = session.get(grade_sheet_url)
                if grade_sheet_response.status_code == 200:
                    soup = BeautifulSoup(grade_sheet_response.content, 'html.parser')
                    table_rows = soup.find_all('tr')
                    course_data = {}
                    total_credits = []
                    for row in table_rows:
                        cells = row.find_all('td')

                        if len(cells) == 6:
                            if 'CUMULATIVE' in cells[0]:
                                total_credits.append((cells[2].get_text(strip=True), cells[3].get_text(strip=True), cells[5].get_text(strip=True)))
                            else:
                                creds = cells[2].get_text(strip=True)
                                if 'SEMESTER' not in cells[0] and int(float(creds)) != 0:
                                    course_name = cells[0].get_text(strip=True)
                                    cgpa = float(cells[5].get_text(strip=True))
                                    course_data[course_name] = cgpa

                this_sem = []
                advised_response = session.get(advised)
                if advised_response.status_code == 200:
                    soup = BeautifulSoup(advised_response.text, 'html.parser')
                    course_rows = soup.find_all('tr')
                    for row in course_rows:
                        cells = row.find_all('td')
                        if 'Course Code' not in cells[0].get_text(strip=True):
                            advised_course = cells[0].get_text(strip=True)
                            this_sem.append(advised_course)

                    total_credits = total_credits[-1][1:]  # (credits completed, current gpa)
                    return jsonify(course_data=course_data, total_credits=total_credits, this_sem=this_sem)

    return jsonify({'error': 'Login failed or failed to fetch data'}), 401

# Setup logging
logging.basicConfig(level=logging.DEBUG)
# @csrf.exempt

@app.route('/calculate_cgpa', methods=['POST'])
def calculate_cgpa():
    data = request.json
    cgpa_data = data.get('imp')['cgpa_data']
    this_sem_data = data.get('sem')['this_sem_data']
    all_course = data.get('mergedData')
    app.logger.debug(f"Received CGPA data: {cgpa_data}")
    app.logger.debug(f"Received this semester data: {this_sem_data}")

    overal = 0
    overal_count = 0

    for course, cgpa in all_course.items():
        overal += float(cgpa)
        overal_count += 1

    if this_sem_data:
        for course, cgpa in this_sem_data.items():
            if course in all_course:
                overal += cgpa - all_course[course]
            else:
                app.logger.debug(f"Processing this semester course: {course}, CGPA: {cgpa}")
                overal += float(cgpa)
                overal_count += 1

    if overal_count == 0:
        return jsonify({'error': 'No valid CGPA data'}), 400

    new_cgpa = overal / overal_count
    app.logger.debug(f"Calculated new CGPA: {new_cgpa}")
    return jsonify({'new_cgpa': round(new_cgpa, 2)})
# @csrf.exempt

@app.route('/check_target_cgpa', methods=['POST'])
def check_target_cgpa():
    data = request.json
    department = data.get('department')
    comp_credits = data.get('comp_credits')
    curr_cgpa = data.get('curr_cgpa')
    target_gpa = data.get('target_gpa')

    if department not in ['cs', 'cse']:
        return jsonify({'error': 'Invalid department'}), 400

    if department == 'cs':
        total_creds = 124
    elif department == 'cse':
        total_creds = 136

    remaining_sem = total_creds - comp_credits
    credCgpa = comp_credits * curr_cgpa
    totalTarget = total_creds * target_gpa
    now = totalTarget - credCgpa
    possible = now / remaining_sem

    if possible > 4:
        return jsonify({'result': 'not possible'})
    else:
        return jsonify({'result': 'possible', 'required_gpa': round(possible, 2)})

if __name__ == '__main__':
    app.run(debug=True, port=5002)
