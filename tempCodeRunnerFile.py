
            dashboard_response = session.get(dashboard_url)

            if dashboard_response.status_code == 200:
                grade_sheet_response = session.get(grade_sheet_url)
                if grade_sheet_response.status_code == 200:
                    soup = BeautifulSoup(grade_sheet_response.content, 'html.parser')
                    table_rows = soup.find_all('tr')
                    course_data = defaultdict(lambda: (0, 0))
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
                                    credits = float(cells[3].get_text(strip=True))
                                    current_cgpa, current_credits = course_data[course_name]
                                    if cgpa > current_cgpa:
                                        course_data[course_name] = (cgpa, credits)  #made a change


                # this_sem = []
                this_sem = defaultdict(lambda: (0, 0))

                advised_response = session.get(advised)
                if advised_response.status_code == 200:
                    soup = BeautifulSoup(advised_response.text, 'html.parser')
                    course_rows = soup.find_all('tr')
                    for row in course_rows:
                        cells = row.find_all('td')
                        if 'Course Code' not in cells[0].get_text(strip=True):
                            credit_persem = cells[4].get_text(strip=True)
                            advised_course = cells[0].get_text(strip=True)
                            # this_sem.append([advised_course, credit_persem])
                            this_sem[advised_course] = (None, credit_persem)
                    total_credits = total_credits[-1][1:]  # (credits completed, current gpa)
                    return jsonify(course_data=course_data, total_credits=total_credits, this_sem=this_sem)

    return jsonify({'error': 'Login failed or failed to fetch data'}), 401

logging.basicConfig(level=logging.DEBUG)

@app.route('/calculate_cgpa', methods=['POST'])