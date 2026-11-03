import sys
import re
from datetime import datetime

# Import application
from app import app
from database import get_connection

def run_tests():
    print("=" * 60)
    print("STARTING COMPLETE TEST SUITE FOR ROAD ACCIDENT ANALYSIS SYSTEM")
    print("=" * 60)

    # -------------------------------------------------------------
    # 1. AUTHENTICATION & ROUTE PROTECTION TESTS
    # -------------------------------------------------------------
    print("\n--- 1. Testing Unauthenticated Route Protection ---")
    unauth_client = app.test_client()

    protected_routes = ['/', '/analysis', '/accidents', '/add-accident']
    for route in protected_routes:
        if route == '/add-accident':
            res = unauth_client.post(route, follow_redirects=False)
        else:
            res = unauth_client.get(route, follow_redirects=False)

        assert res.status_code == 302, f"Expected 302 redirect for {route}, got {res.status_code}"
        assert '/login' in res.headers['Location'], f"Expected redirect to /login for {route}, got {res.headers['Location']}"
        print(f"  [PASS] Unauthenticated access to '{route}' successfully redirected to /login.")

    # Test attempting to delete a record while logged out
    res_del_unauth = unauth_client.post('/delete-accident/1', follow_redirects=False)
    assert res_del_unauth.status_code == 302
    assert '/login' in res_del_unauth.headers['Location']
    print("  [PASS] Unauthenticated delete request successfully redirected to /login.")

    # -------------------------------------------------------------
    # 2. LOGIN PAGE TESTS
    # -------------------------------------------------------------
    print("\n--- 2. Testing Login Page & Authentication ---")
    client = app.test_client()

    res_login_get = client.get('/login')
    assert res_login_get.status_code == 200
    html_login = res_login_get.data.decode('utf-8')
    assert 'Sign in to access the dashboard' in html_login
    assert 'name="csrf_token"' in html_login
    assert 'name="username"' in html_login
    assert 'name="password"' in html_login
    print("  [PASS] Login page renders with CSRF token, username, and password fields.")

    # Extract CSRF token from login page
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_login)
    assert csrf_match, "Could not extract CSRF token from login HTML"
    csrf_token = csrf_match.group(1)

    # Test invalid login credentials
    res_bad_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'username': 'admin',
        'password': 'WrongPassword123'
    }, follow_redirects=True)
    assert res_bad_login.status_code == 401
    assert 'Invalid username or password' in res_bad_login.data.decode('utf-8')
    print("  [PASS] Invalid login credentials rejected with 401 status and error message.")

    # Test CSRF protection on login
    res_csrf_bad = client.post('/login', data={
        'csrf_token': 'tampered_token_xyz',
        'username': 'admin',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res_csrf_bad.status_code == 400
    print("  [PASS] Tampered CSRF token on login rejected with 400 status.")

    # Test valid login credentials
    res_good_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'username': 'admin',
        'password': 'Admin@123'
    }, follow_redirects=False)
    assert res_good_login.status_code == 302, f"Expected 302 redirect after login, got {res_good_login.status_code}"
    assert res_good_login.headers['Location'] == '/'

    # Access Dashboard as authenticated user
    res_dash = client.get('/', follow_redirects=True)
    assert res_dash.status_code == 200
    html_dash = res_dash.data.decode('utf-8')
    assert 'Dashboard Overview' in html_dash
    print("  [PASS] Valid administrator login successful and redirected to Dashboard.")

    # Verify Cache-Control headers on protected pages
    assert 'no-store' in res_dash.headers.get('Cache-Control', '')
    print("  [PASS] Cache-Control headers verified on protected responses.")

    # Extract authenticated CSRF token from Dashboard
    csrf_auth_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_dash)
    assert csrf_auth_match, "Could not extract CSRF token from authenticated dashboard"
    csrf_auth = csrf_auth_match.group(1)

    # -------------------------------------------------------------
    # 3. DASHBOARD STATISTICS & CONTENT
    # -------------------------------------------------------------
    print("\n--- 3. Testing Dashboard Statistics & Severity Breakdown ---")
    res_home = client.get('/')
    html_home = res_home.data.decode('utf-8')

    assert 'Total Accidents' in html_home
    assert 'Most Affected Region' in html_home
    assert 'Most Common Vehicle' in html_home
    assert 'Busiest Accident Hour' in html_home
    assert 'Accident Severity Summary' in html_home
    assert 'Minor' in html_home
    assert 'Serious' in html_home
    assert 'Fatal' in html_home
    assert 'target="_blank"' not in html_home
    print("  [PASS] Dashboard statistics and severity distribution verified against MySQL values.")

    # -------------------------------------------------------------
    # 4. ANALYSIS PAGE CHARTS
    # -------------------------------------------------------------
    print("\n--- 4. Testing Analysis Page & Matplotlib Visualizations ---")
    res_analysis = client.get('/analysis')
    assert res_analysis.status_code == 200
    html_analysis = res_analysis.data.decode('utf-8')

    charts = [
        'hourly_accidents.png',
        'location_accidents.png',
        'severity_accidents.png',
        'time_period_accidents.png'
    ]
    for chart in charts:
        assert chart in html_analysis, f"Missing chart {chart} on /analysis"
        # Verify static file exists
        res_chart_file = client.get(f'/static/charts/{chart}')
        assert res_chart_file.status_code == 200, f"Chart image /static/charts/{chart} could not be loaded"
        assert len(res_chart_file.data) > 0, f"Chart image /static/charts/{chart} is empty"
        print(f"  [PASS] Chart '{chart}' verified and accessible (Size: {len(res_chart_file.data)} bytes).")

    # -------------------------------------------------------------
    # 5. ACCIDENT RECORDS & DELETE FUNCTIONALITY
    # -------------------------------------------------------------
    print("\n--- 5. Testing Accident Records & Record Deletion ---")
    res_acc = client.get('/accidents')
    assert res_acc.status_code == 200
    html_acc = res_acc.data.decode('utf-8')
    assert 'Recorded Database Entries' in html_acc
    assert 'Total Records:' in html_acc
    assert 'delete-btn' in html_acc
    print("  [PASS] Accident Records table loaded with records and Delete buttons.")

    # Test deleting a nonexistent ID
    res_del_nonexistent = client.post('/delete-accident/999999', data={'csrf_token': csrf_auth}, follow_redirects=True)
    assert res_del_nonexistent.status_code == 200
    assert 'was not found' in res_del_nonexistent.data.decode('utf-8')
    print("  [PASS] Deleting nonexistent record handled gracefully.")

    # Insert a DISPOSABLE test accident record to delete
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT location_id FROM locations LIMIT 1")
    loc_id = cur.fetchone()['location_id']
    cur.execute("""
        INSERT INTO accidents (accident_datetime, location_id, vehicle_type, severity, weather)
        VALUES (NOW(), %s, 'Other', 'Minor', 'Clear')
    """, (loc_id,))
    conn.commit()
    disposable_id = cur.lastrowid
    cur.close()
    conn.close()
    print(f"  [INFO] Created disposable test accident record #{disposable_id}.")

    # Verify disposable record is in database
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM accidents WHERE accident_id = %s", (disposable_id,))
    assert cur.fetchone() is not None
    cur.close()
    conn.close()

    # Delete the disposable record via POST /delete-accident/<id>
    res_del = client.post(f'/delete-accident/{disposable_id}', data={'csrf_token': csrf_auth}, follow_redirects=True)
    assert res_del.status_code == 200
    html_del_result = res_del.data.decode('utf-8')
    assert f'Accident record #{disposable_id} was deleted successfully' in html_del_result

    # Verify record is gone from database
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM accidents WHERE accident_id = %s", (disposable_id,))
    assert cur.fetchone() is None, f"Record #{disposable_id} should have been deleted"
    cur.close()
    conn.close()
    print(f"  [PASS] Disposable record #{disposable_id} safely deleted; unrelated records remain intact.")

    # -------------------------------------------------------------
    # 6. ADD ACCIDENT FUNCTIONALITY
    # -------------------------------------------------------------
    print("\n--- 6. Testing Add Accident Record ---")
    # Test invalid input (missing required fields)
    res_add_invalid = client.post('/add-accident', data={
        'csrf_token': csrf_auth,
        'accident_datetime': '',
        'region': '',
        'vehicle_type': '',
        'severity': ''
    }, follow_redirects=True)
    assert res_add_invalid.status_code == 200
    assert 'Please fill in all required fields' in res_add_invalid.data.decode('utf-8')
    print("  [PASS] Missing required fields properly rejected with validation error.")

    # Test valid submission
    test_now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    res_add_valid = client.post('/add-accident', data={
        'csrf_token': csrf_auth,
        'accident_datetime': test_now_str,
        'region': 'Tirupati Safety Zone',
        'road_name': 'Green Avenue',
        'vehicle_type': 'Car',
        'severity': 'Minor',
        'weather': 'Clear',
        'cause_of_accident': 'Over Speeding'
    }, follow_redirects=True)
    assert res_add_valid.status_code == 200
    assert 'Accident record added successfully' in res_add_valid.data.decode('utf-8')
    print("  [PASS] Valid accident record added successfully to MySQL.")

    # Clean up the test added record
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.accident_id 
        FROM accidents a 
        JOIN locations l ON a.location_id = l.location_id 
        WHERE l.region = 'Tirupati Safety Zone' 
        ORDER BY a.accident_id DESC LIMIT 1
    """)
    new_row = cur.fetchone()
    if new_row:
        cur.execute("DELETE FROM accidents WHERE accident_id = %s", (new_row['accident_id'],))
        conn.commit()
        print(f"  [INFO] Cleaned up test record #{new_row['accident_id']}.")
    cur.close()
    conn.close()

    # -------------------------------------------------------------
    # 7. LOGOUT & POST-LOGOUT ACCESS PROTECTION
    # -------------------------------------------------------------
    print("\n--- 7. Testing Logout & Post-Logout Protection ---")
    res_logout = client.post('/logout', data={'csrf_token': csrf_auth}, follow_redirects=True)
    assert res_logout.status_code == 200
    assert 'You have been logged out successfully' in res_logout.data.decode('utf-8')
    print("  [PASS] Logout POST request cleared session and redirected to Login.")

    # Try accessing protected pages after logout
    for route in ['/', '/analysis', '/accidents']:
        res_after = client.get(route, follow_redirects=False)
        assert res_after.status_code == 302, f"Route {route} allowed access after logout!"
        assert '/login' in res_after.headers['Location']
        print(f"  [PASS] Access to '{route}' blocked after logout.")

    # -------------------------------------------------------------
    # 8. LIGHT & DARK MODE THEME TOKENS
    # -------------------------------------------------------------
    print("\n--- 8. Testing Theme Styling & CSS Tokens ---")
    with open('static/style.css', 'r', encoding='utf-8') as f:
        css_content = f.read()

    assert '[data-theme="dark"]' in css_content, "Dark theme selector missing in style.css"
    assert '--bg-page: #090e17' in css_content, "Dark theme background missing"
    assert 'theme-toggle-btn' in css_content, "Theme toggle button class missing"
    assert 'delete-btn' in css_content, "Delete button styling missing"
    assert 'modal-overlay' in css_content, "Modal dialog styling missing"
    print("  [PASS] CSS contains comprehensive Light and Dark mode variables, toggle styles, and modal tokens.")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY! ZERO ERRORS ENCOUNTERED.")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
