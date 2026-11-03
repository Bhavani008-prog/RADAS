import re
from datetime import datetime
from app import app
from database import get_connection

def test_full_auth_and_signup():
    print("=" * 65)
    print("TESTING USER SIGN UP & AUTHENTICATION UPGRADE")
    print("=" * 65)

    client = app.test_client()

    # -------------------------------------------------------------
    # 1. VERIFY LOGIN PAGE DESIGN & REMOVAL OF DEFAULT ADMIN TEXT
    # -------------------------------------------------------------
    print("\n--- 1. Testing Login Page & Links ---")
    res_login = client.get('/login')
    assert res_login.status_code == 200
    html_login = res_login.data.decode('utf-8')

    # Must NOT have default admin text
    assert 'Default administrator: admin / Admin@123' not in html_login, \
        "FAILURE: 'Default administrator: admin / Admin@123' must be removed from login page!"
    assert 'Admin@123' not in html_login, "FAILURE: Plain text password found in login page HTML!"
    print("  [PASS] 'Default administrator: admin / Admin@123' is successfully removed from login page.")

    # Must have Sign Up link
    assert "Don't have an account?" in html_login, "FAILURE: 'Don't have an account?' text missing!"
    assert 'href="/signup"' in html_login, "FAILURE: Link to /signup missing from login page!"
    print("  [PASS] Visible 'Don't have an account? Sign Up' link verified on login page.")

    # Extract CSRF token from Login
    csrf_login = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_login).group(1)

    # -------------------------------------------------------------
    # 2. VERIFY SIGN UP PAGE
    # -------------------------------------------------------------
    print("\n--- 2. Testing Sign Up Page ---")
    res_signup = client.get('/signup')
    assert res_signup.status_code == 200
    html_signup = res_signup.data.decode('utf-8')

    assert 'Create an account to access the dashboard' in html_signup
    assert 'name="username"' in html_signup
    assert 'name="password"' in html_signup
    assert 'name="confirm_password"' in html_signup
    assert 'Create Account' in html_signup
    assert 'Already have an account?' in html_signup
    assert 'href="/login"' in html_signup
    print("  [PASS] Sign Up page renders with Username, Password, Confirm Password, Create Account button, and link to Sign In.")

    csrf_signup = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_signup).group(1)

    # -------------------------------------------------------------
    # 3. TEST SIGN UP VALIDATION RULES
    # -------------------------------------------------------------
    print("\n--- 3. Testing Sign Up Validations ---")

    # A. Missing fields
    res_missing = client.post('/signup', data={
        'csrf_token': csrf_signup,
        'username': '',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    assert res_missing.status_code == 400
    assert 'Please fill in all fields' in res_missing.data.decode('utf-8')
    print("  [PASS] Missing username rejected with 'Please fill in all fields.'")

    # B. Password < 8 characters
    res_short = client.post('/signup', data={
        'csrf_token': csrf_signup,
        'username': 'testuser_short',
        'password': '12345',
        'confirm_password': '12345'
    }, follow_redirects=True)
    assert res_short.status_code == 400
    assert 'Password must be at least 8 characters long' in res_short.data.decode('utf-8')
    print("  [PASS] Short password (< 8 chars) rejected with 'Password must be at least 8 characters long.'")

    # C. Passwords do not match
    res_mismatch = client.post('/signup', data={
        'csrf_token': csrf_signup,
        'username': 'testuser_mismatch',
        'password': 'Password@123',
        'confirm_password': 'DifferentPassword@123'
    }, follow_redirects=True)
    assert res_mismatch.status_code == 400
    assert 'Passwords do not match. Please try again.' in res_mismatch.data.decode('utf-8')
    print("  [PASS] Password mismatch rejected with 'Passwords do not match. Please try again.'")

    # D. Duplicate username (test with existing 'admin')
    res_dup = client.post('/signup', data={
        'csrf_token': csrf_signup,
        'username': 'admin',
        'password': 'NewPassword@123',
        'confirm_password': 'NewPassword@123'
    }, follow_redirects=True)
    assert res_dup.status_code == 409
    assert 'Username already exists. Please choose another.' in res_dup.data.decode('utf-8')
    print("  [PASS] Duplicate username rejected with 'Username already exists. Please choose another.'")

    # -------------------------------------------------------------
    # 4. TEST SUCCESSFUL REGISTRATION
    # -------------------------------------------------------------
    print("\n--- 4. Testing Successful User Registration ---")
    test_user = f"new_driver_{int(datetime.now().timestamp())}"
    test_pass = "SecurePass@2026"

    # Make sure user doesn't already exist
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("DELETE FROM users WHERE username = %s", (test_user,))
    conn.commit()
    cur.close()
    conn.close()

    res_reg = client.post('/signup', data={
        'csrf_token': csrf_signup,
        'username': test_user,
        'password': test_pass,
        'confirm_password': test_pass
    }, follow_redirects=False)

    assert res_reg.status_code == 302, f"Expected 302 redirect after signup, got {res_reg.status_code}"
    assert res_reg.headers['Location'] == '/login', f"Expected redirect to /login, got {res_reg.headers['Location']}"

    # Follow redirect to login page and check success flash message
    res_after_signup = client.get('/login')
    html_after_signup = res_after_signup.data.decode('utf-8')
    assert 'Account created successfully. Please sign in.' in html_after_signup
    print(f"  [PASS] User '{test_user}' registered successfully and redirected to Login with success message.")

    # Verify user exists in MySQL with hashed password
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s", (test_user,))
    created_user = cur.fetchone()
    assert created_user is not None, "User not found in MySQL users table!"
    assert created_user['password_hash'] != test_pass, "Password was stored in plain text!"
    assert created_user['password_hash'].startswith('scrypt:') or len(created_user['password_hash']) > 20
    cur.close()
    conn.close()
    print("  [PASS] Verified in MySQL: Password is encrypted with secure password hashing (no plain text).")

    # -------------------------------------------------------------
    # 5. TEST LOGIN WITH NEWLY CREATED CREDENTIALS
    # -------------------------------------------------------------
    print("\n--- 5. Testing Sign In with New User ---")
    csrf_new_login = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_after_signup).group(1)

    # Test bad password for new user
    res_bad = client.post('/login', data={
        'csrf_token': csrf_new_login,
        'username': test_user,
        'password': 'WrongPassword@999'
    }, follow_redirects=True)
    assert res_bad.status_code == 401
    assert 'Invalid username or password.' in res_bad.data.decode('utf-8')
    print("  [PASS] Invalid password for new user correctly rejected.")

    # Test good password for new user
    res_login_ok = client.post('/login', data={
        'csrf_token': csrf_new_login,
        'username': test_user,
        'password': test_pass
    }, follow_redirects=False)
    assert res_login_ok.status_code == 302
    assert res_login_ok.headers['Location'] == '/'

    # Access Dashboard
    res_dash = client.get('/', follow_redirects=True)
    assert res_dash.status_code == 200
    html_dash = res_dash.data.decode('utf-8')
    assert 'Dashboard Overview' in html_dash
    assert f'Welcome back, {test_user}!' in html_dash or test_user in html_dash
    print(f"  [PASS] New user '{test_user}' successfully signed in and accessed the Dashboard.")

    csrf_dash = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_dash).group(1)

    # -------------------------------------------------------------
    # 6. TEST NAVIGATION ACROSS PROTECTED PAGES WITH NEW USER
    # -------------------------------------------------------------
    print("\n--- 6. Testing Navigation & Features with New User Session ---")
    res_analysis = client.get('/analysis')
    assert res_analysis.status_code == 200
    assert 'hourly_accidents.png' in res_analysis.data.decode('utf-8')
    print("  [PASS] New user accessed /analysis and charts.")

    res_accidents = client.get('/accidents')
    assert res_accidents.status_code == 200
    assert 'Recorded Database Entries' in res_accidents.data.decode('utf-8')
    assert 'delete-btn' in res_accidents.data.decode('utf-8')
    print("  [PASS] New user accessed /accidents and records table.")

    # -------------------------------------------------------------
    # 7. TEST ADD ACCIDENT & DELETE ACCIDENT WITH NEW USER
    # -------------------------------------------------------------
    print("\n--- 7. Testing Add & Delete Accident with New User ---")
    test_time = datetime.now().strftime("%Y-%m-%dT%H:%M")
    res_add = client.post('/add-accident', data={
        'csrf_token': csrf_dash,
        'accident_datetime': test_time,
        'region': 'New User Test Sector',
        'road_name': 'Signup Highway',
        'vehicle_type': 'Bike',
        'severity': 'Minor',
        'weather': 'Clear',
        'cause_of_accident': 'Rash Driving'
    }, follow_redirects=True)
    assert res_add.status_code == 200
    assert 'Accident record added successfully!' in res_add.data.decode('utf-8')
    print("  [PASS] New user successfully added an accident record.")

    # Find the added record and delete it
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.accident_id FROM accidents a
        JOIN locations l ON a.location_id = l.location_id
        WHERE l.region = 'New User Test Sector'
        ORDER BY a.accident_id DESC LIMIT 1
    """)
    added_row = cur.fetchone()
    assert added_row is not None
    added_id = added_row['accident_id']
    cur.close()
    conn.close()

    res_del = client.post(f'/delete-accident/{added_id}', data={'csrf_token': csrf_dash}, follow_redirects=True)
    assert res_del.status_code == 200
    assert f'Accident record #{added_id} was deleted successfully.' in res_del.data.decode('utf-8')
    print(f"  [PASS] New user successfully deleted accident record #{added_id}.")

    # -------------------------------------------------------------
    # 8. TEST LOGOUT & ACCESS REJECTION AFTER LOGOUT
    # -------------------------------------------------------------
    print("\n--- 8. Testing Logout & Access Rejection ---")
    res_logout = client.post('/logout', data={'csrf_token': csrf_dash}, follow_redirects=True)
    assert res_logout.status_code == 200
    assert 'You have been logged out successfully.' in res_logout.data.decode('utf-8')
    print("  [PASS] New user successfully logged out via POST /logout.")

    for route in ['/', '/analysis', '/accidents']:
        res_blocked = client.get(route, follow_redirects=False)
        assert res_blocked.status_code == 302
        assert '/login' in res_blocked.headers['Location']
        print(f"  [PASS] Access to '{route}' blocked after logout.")

    # -------------------------------------------------------------
    # 9. CLEAN UP TEST USER & VERIFY ACCIDENTS INTACT
    # -------------------------------------------------------------
    print("\n--- 9. Cleanup & Final Database Integrity Check ---")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("DELETE FROM users WHERE username = %s", (test_user,))
    conn.commit()

    cur.execute("SELECT COUNT(*) as count FROM accidents")
    acc_count = cur.fetchone()['count']
    assert acc_count == 5, f"Expected 5 original accident records, found {acc_count}!"
    print(f"  [PASS] Cleaned up temporary test user. All {acc_count} original accident records are completely intact.")
    cur.close()
    conn.close()

    print("\n" + "=" * 65)
    print("ALL 9 AUTHENTICATION & SIGNUP TEST SUITES PASSED WITH ZERO ERRORS!")
    print("=" * 65)

if __name__ == '__main__':
    test_full_auth_and_signup()

