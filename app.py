
import os
import time
import re
import json
import pdfplumber
import requests
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_wtf.csrf import CSRFProtect, generate_csrf
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
from flask_talisman import Talisman

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Make CSRF token available in templates
app.jinja_env.globals['csrf_token'] = generate_csrf

# Setup Flask-Talisman (fixes inline CSS issues)
Talisman(app, content_security_policy={
    'default-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
    'script-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", "data:", "https://img.icons8.com"],  # ✅ Allow external images
})

# logging.basicConfig(level=logging.DEBUG)

########################################
# HELPER FUNCTIONS
########################################

def get_total_credits(department):
    dept_credits = {
        'cs': 124,
        'cse': 136,
        'archi': 207,
        'eee': 136,
        'bba': 130,
        'econ': 120,
        'llb': 135,
        'math': 127,
        'microbio': 136,
        'pharmacy': 164,
        'physics': 132,
        'anth': 120,
        'ape': 130,
        'biotech': 136,
        'baeng': 120,
        'ece': 136
    }
    return dept_credits.get(department)

def extract_grade_sheet(pdf_path):
    """
    Opens the downloaded PDF and extracts:
      - Student details (Student ID, Name, Program)
      - Course records: each record is a list:
            [course_code, course_title, credits, grade, grade_points]
        Only courses with credits > 0 are kept.
      - Cumulative data: every cumulative record (e.g., "Credits Attempted 54.00 ... CGPA 3.51")
        is collected; the final cumulative record is used.
    """
    student_info = {}
    courses_dict = {}
    cumulative_data = []  # List of tuples: (credits_attempted, cgpa)
    cumulative_pattern = r"Credits Attempted\s+([\d\.]+).*CGPA\s+([\d\.]+)"
    address_keywords = ["Avenue", "Dhaka", "Badda"]
    
    lines_all = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines_all.extend(text.split("\n"))
    
    for line in lines_all:
        tokens = line.split()
        if not tokens:
            continue
        # If the line is a cumulative header, extract cumulative info.
        if tokens[0].upper() in ["SEMESTER", "SEMESTER:", "CUMULATIVE"]:
            match = re.search(cumulative_pattern, line)
            if match:
                cumulative_data.append((float(match.group(1)), float(match.group(2))))
            continue
        if tokens[0] == 'Name':
            name = ''
            for i in tokens:
                if i == 'Name' or i == ':':
                    continue
                elif i == 'PROGRAM:':
                    break
                name += i + ' '
            
            student_info['Name'] = name[:-1]

        if len(tokens) < 4:
            continue
        
        try:
            if len(tokens[0]) == 6:
                course_code = tokens[0]    # Fix here about the repeat
                course_title = " ".join(tokens[1:-3])
                if any(keyword in course_title for keyword in address_keywords):
                    continue
                if '(' in tokens[-2]:  # if it's a repeat course then -4 is the credit value
                    credits = float(tokens[-4])
                    grade = tokens[-3]
                else:
                    credits = float(tokens[-3])
                    grade = tokens[-2]

                grade_points = float(tokens[-1])
            

                if credits > 0:
                    if course_code in courses_dict:
                        if courses_dict[course_code][-1] > grade_points:
                            continue
                        else:
                            courses_dict[course_code] = [course_code, course_title, credits, grade, grade_points]

                    else:
                        courses_dict[course_code] = [course_code, course_title, credits, grade, grade_points]
         
        except ValueError:
            continue
    app.logger.debug(f"Extracted courses dict: {courses_dict}")
    courses = list(courses_dict.values())
    final_cumulative = cumulative_data[-1] if cumulative_data else None
    return student_info, courses, final_cumulative

def compute_cgpa(courses):
    total_credits = sum(course[2] for course in courses)
    if total_credits == 0:
        return None
    total_grade_points = sum(course[2] * course[4] for course in courses)
    return total_grade_points / total_credits

def process_grade_sheet(username, password):
    """
    Uses headless Selenium to log into the portal, download the PDF,
    and extract student info, course records, and cumulative data.
    Ensures that the PDF is deleted even if extraction fails or disconnects.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.binary_location = "/usr/bin/google-chrome"

    download_path = os.getcwd()
    prefs = {"download.default_directory": download_path}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=chrome_options)
    pdf_filename = None

    try:
        driver.get("https://sso.bracu.ac.bd/realms/bracu/protocol/openid-connect/auth?client_id=slm&redirect_uri=https%3A%2F%2Fconnect.bracu.ac.bd%2F")
        time.sleep(3)
        username_input = driver.find_element(By.ID, "username")
        password_input = driver.find_element(By.ID, "password")
        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        driver.get("https://connect.bracu.ac.bd/student/grade-sheet")
        time.sleep(3)
        
        try:
            download_button = driver.find_element(By.CLASS_NAME, "btn.btn-info")
            download_button.click()
            app.logger.debug("Grade sheet download initiated...")
        except Exception as e:
            raise Exception("Could not locate or click the download button: " + str(e))
        
        time.sleep(10)

        # Find downloaded PDF
        for file in os.listdir(download_path):
            if file.startswith("grade-sheet") and file.endswith(".pdf"):
                pdf_filename = os.path.join(download_path, file)
                break

        if not pdf_filename:
            raise Exception("Downloaded grade sheet PDF not found!")

        # **Ensure the file is removed even if an error occurs**
        try:
            student_info, courses, final_cumulative = extract_grade_sheet(pdf_filename)
            if final_cumulative:
                completed_credits, current_cgpa = final_cumulative
            else:
                completed_credits = sum(course[2] for course in courses)
                current_cgpa = compute_cgpa(courses)
        finally:
            if pdf_filename and os.path.exists(pdf_filename):
                os.remove(pdf_filename)
                app.logger.debug(f"Deleted PDF: {pdf_filename}")

    except Exception as e:
        app.logger.error(f"Error in processing grade sheet: {e}")

    finally:
        driver.quit()
    
    return student_info, courses, current_cgpa, completed_credits, final_cumulative

def process_schedule(username, password):
    """
    Uses headless Selenium (with performance logging enabled) to log into the portal,
    click on "Class and Exam Schedule", extract the Bearer token from network logs,
    and then use it to fetch the course schedule via the API.
    Returns the schedule data as a list of course dictionaries, with the 'sectionSchedule'
    field parsed into a 'schedule_details' dictionary.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    options.binary_location = "/usr/bin/google-chrome"

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome('/usr/local/bin/chromedriver', options=chrome_options)
    schedule_data = None
    try:
        driver.get("https://sso.bracu.ac.bd/realms/bracu/protocol/openid-connect/auth?client_id=slm&redirect_uri=https%3A%2F%2Fconnect.bracu.ac.bd%2F")
        time.sleep(3)
        username_input = driver.find_element(By.ID, "username")
        password_input = driver.find_element(By.ID, "password")
        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)
        
        # Click on "Class and Exam Schedule"
        class_schedule_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Class and Exam Schedule')]"))
        )
        class_schedule_button.click()
        time.sleep(5)
        
        # Extract network logs to search for the Authorization token
        logs = driver.get_log("performance")
        access_token = None
        for log in logs:
            try:
                log_data = json.loads(log["message"])["message"]
                if "Authorization" in str(log_data):
                    headers = log_data.get("params", {}).get("request", {}).get("headers", {})
                    if "Authorization" in headers:
                        access_token = headers["Authorization"].replace("Bearer ", "")
                        break
            except Exception:
                continue
        
        if not access_token:
            raise Exception("Could not extract access token from network logs.")
        
        # Use the extracted token to fetch the schedule data via the API
        schedule_url = "https://connect.bracu.ac.bd/api/adv/v1/student-courses/schedules?studentPortfolioId=44316"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://connect.bracu.ac.bd/student/schedule",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-Realm": "bracu"
        }
        schedule_response = requests.get(schedule_url, headers=headers)
        if schedule_response.status_code == 200:
            schedule_data = schedule_response.json()
            # Parse the JSON in each course's sectionSchedule field for easier rendering
            for course in schedule_data:
                course["schedule_details"] = json.loads(course["sectionSchedule"])
        else:
            raise Exception(f"Schedule API returned status code {schedule_response.status_code}")
    finally:
        driver.quit()
    return schedule_data

def calculate_credits(all_course):
    print('\n')
    print('#############################################')
    print('all course:     ', all_course)
    print('\n')

    total_credits = 0
    creds_cgpa = 0
    for course, values in all_course.items():
        total_credits += values[1]
        creds_cgpa += float(values[0] * values[1])

   
    return total_credits, creds_cgpa

def calculate_this_sem_credits(this_sem_data, all_course, total_credits, creds_cgpa):
    print('#############################################')
    print('this semm_data:     ', this_sem_data)
    print('###################')
    print('ALL COUORSE', all_course)
    for course, cgpa in this_sem_data.items():
        if course in all_course:
            repeat = all_course[course][0] * all_course[course][1]
            creds_cgpa -= repeat
            creds_cgpa += (cgpa[0] * cgpa[1])
        else:
            total_credits += cgpa[1]
            creds_cgpa += float(cgpa[0] * cgpa[1])
    return total_credits, creds_cgpa

########################################
# ROUTES
########################################

@app.route("/", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            student_info, courses, current_cgpa, completed_credits, cumulative_data = process_grade_sheet(username, password)
            # Also extract course schedule data
            schedule_data = process_schedule(username, password)
            session["student_info"] = student_info
            session["courses"] = courses
            session["cgpa"] = current_cgpa
            session["completed_credits"] = completed_credits
            session["cumulative_data"] = cumulative_data
            session["schedule_data"] = schedule_data
            flash("Grade sheet and schedule data successfully extracted!")
            return redirect(url_for("dashboard"))
        except Exception as e:
            flash("Error during processing: " + str(e))
            return redirect(url_for("login_page"))
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    student_info = session.get("student_info", "user")
    cgpa = session.get("cgpa")
    completed_credits = session.get("completed_credits", 0)
    courses = session.get("courses", [])
    cumulative_data = session.get("cumulative_data", None)
    schedule_data = session.get("schedule_data", [])
    print(student_info)
    return render_template("dashboard.html",
                           student_info=student_info,
                           cgpa=cgpa,
                           completed_credits=completed_credits,
                           courses=courses,
                           cumulative_data=cumulative_data,
                           schedule_data=schedule_data)

@app.route("/calculate_cgpa", methods=["POST"])
def calculate_cgpa_route():
    data = request.json
    cgpa_data = data.get('imp')['cgpa_data']  # dict: course_code -> [new_grade, credits]
    # For improved grades, we treat the updated data as "this_sem_data"
    this_sem_data = data.get('sem')['this_sem_data'] if data.get('sem') else {}
    all_course = data.get('mergedData')
    app.logger.debug(f"Received merged data: {all_course}")
    try:
        total_credits, creds_cgpa = calculate_credits(all_course)
        if this_sem_data:
            print('yes', this_sem_data)
            total_credits, creds_cgpa = calculate_this_sem_credits(this_sem_data, all_course, total_credits, creds_cgpa)

    
        print(total_credits, creds_cgpa)
        new_cgpa = round(creds_cgpa / total_credits, 2)
        app.logger.debug(f"Calculated new CGPA: {new_cgpa}")
        return jsonify({'new_cgpa': new_cgpa})
    except Exception as e:
        app.logger.error(f"Error during CGPA calculation: {e}")
        return jsonify({'error': 'Calculation failed'}), 500

@app.route("/check_target_cgpa", methods=["POST"])
def check_target_cgpa():
    data = request.json
    department = data.get("department")
    try:
        comp_credits = float(data.get("comp_credits", 0))
        curr_cgpa = float(data.get("curr_cgpa", 0))
        target_gpa = float(data.get("target_gpa", 0))
    except ValueError:
        return jsonify({'error': 'Invalid numerical values provided.'}), 400

    # Validate target GPA (should not exceed 4.00)
    if target_gpa > 4:
        return jsonify({'result': 'invalid'}), 200

    total_credits = get_total_credits(department)
    if not total_credits:
        return jsonify({'error': 'Invalid department provided.'}), 400

    # Calculate the required GPA for the remaining credits
    remaining_credits = total_credits - comp_credits
    current_total_points = curr_cgpa * comp_credits
    target_total_points = target_gpa * total_credits
    required_points = target_total_points - current_total_points

    # Avoid division by zero
    if remaining_credits <= 0:
        return jsonify({'error': 'No remaining credits to improve.'}), 400

    required_gpa = required_points / remaining_credits

    return jsonify({
        'result': target_gpa,
        'required_gpa': round(required_gpa, 2)
    })

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for("login_page"))

if __name__ == "__main__":
    app.run(debug=True)
