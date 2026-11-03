"""
Test suite for 'Cause of Accident' feature in Road Accident Data Analysis System.
"""
from datetime import datetime
from bs4 import BeautifulSoup
from app import app
from database import get_connection

def run_tests():
    print("=" * 65)
    print("TESTING CAUSE OF ACCIDENT FEATURE")
    print("=" * 65)

    client = app.test_client()

    # Login as admin
    res_login_page = client.get('/login')
    soup_login = BeautifulSoup(res_login_page.data.decode('utf-8'), 'html.parser')
    csrf_token = soup_login.find('input', {'name': 'csrf_token'})['value']

    res_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'username': 'admin',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res_login.status_code == 200, f"Login failed: status {res_login.status_code}"

    # Extract authenticated CSRF token
    soup_dash = BeautifulSoup(res_login.data.decode('utf-8'), 'html.parser')
    auth_csrf = soup_dash.find('input', {'name': 'csrf_token'})['value']

    # -------------------------------------------------------------------------
    # 1. VERIFY FORM FIELDS ON DASHBOARD (/ OR #add-accident)
    # -------------------------------------------------------------------------
    print("\n--- 1. Testing Add Accident Form Fields ---")
    res_home = client.get('/')
    soup_home = BeautifulSoup(res_home.data.decode('utf-8'), 'html.parser')

    cause_select = soup_home.find('select', {'name': 'cause_of_accident'})
    assert cause_select is not None, "Dropdown 'cause_of_accident' not found in Add Accident form"
    assert cause_select.has_attr('required'), "Dropdown 'cause_of_accident' must be required"

    options = [opt.get_text(strip=True) for opt in cause_select.find_all('option') if opt.get('value')]
    print(f"  Found cause dropdown options: {options}")

    required_options = [
        "Rash Driving",
        "Over Speeding",
        "Drunk Driving",
        "Street Light Problem",
        "Poor Road Conditions",
        "Distracted Driving",
        "Traffic Rule Violation",
        "Other"
    ]
    for opt in required_options:
        assert opt in options, f"Missing required cause option: '{opt}'"
    print("  [PASS] All 8 required dropdown options verified in Add Accident form.")

    other_input = soup_home.find('input', {'name': 'other_cause'})
    assert other_input is not None, "Conditional input 'other_cause' not found in Add Accident form"
    print("  [PASS] Custom cause input field 'other_cause' verified in Add Accident form.")

    # -------------------------------------------------------------------------
    # 2. VERIFY ACCIDENT RECORDS TABLE HEADER & EXISTING DATA
    # -------------------------------------------------------------------------
    print("\n--- 2. Testing Accident Records Table Column & Existing Records ---")
    res_acc = client.get('/accidents')
    soup_acc = BeautifulSoup(res_acc.data.decode('utf-8'), 'html.parser')

    headers = [th.get_text(strip=True).upper() for th in soup_acc.find('thead').find_all('th')]
    print(f"  Table headers found: {headers}")
    assert any("CAUSE OF ACCIDENT" in h for h in headers), f"'CAUSE OF ACCIDENT' column missing from table headers: {headers}"
    print("  [PASS] 'CAUSE OF ACCIDENT' column verified in records table.")

    rows = soup_acc.find('tbody').find_all('tr')
    for r in rows:
        tds = r.find_all('td')
        if len(tds) >= 9:
            # Cause column is index 8 (S.No=0, ID=1, DateTime=2, Region=3, Road=4, Vehicle=5, Severity=6, Weather=7, Cause=8, Actions=9)
            cause_text = tds[8].get_text(strip=True)
            assert cause_text != "", "Cause cell should not be blank"
    print("  [PASS] All existing accident records display valid cause values (e.g. 'Not Specified').")

    # -------------------------------------------------------------------------
    # 3. TEST VALIDATION: MISSING CAUSE & MISSING 'OTHER' SPECIFICATION
    # -------------------------------------------------------------------------
    print("\n--- 3. Testing Form Validation ---")
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M")

    # Submit without cause
    res_no_cause = client.post('/add-accident', data={
        'csrf_token': auth_csrf,
        'accident_datetime': now_str,
        'region': 'Validation Zone',
        'vehicle_type': 'Car',
        'severity': 'Minor',
        'weather': 'Clear',
        'cause_of_accident': ''
    }, follow_redirects=True)
    assert res_no_cause.status_code == 200
    assert "Please" in res_no_cause.data.decode('utf-8')
    print("  [PASS] Submission without cause properly rejected.")

    # Submit with 'Other' but empty 'other_cause'
    res_empty_other = client.post('/add-accident', data={
        'csrf_token': auth_csrf,
        'accident_datetime': now_str,
        'region': 'Validation Zone',
        'vehicle_type': 'Car',
        'severity': 'Minor',
        'weather': 'Clear',
        'cause_of_accident': 'Other',
        'other_cause': ''
    }, follow_redirects=True)
    assert res_empty_other.status_code == 200
    assert "specific cause" in res_empty_other.data.decode('utf-8').lower()
    print("  [PASS] Selecting 'Other' without specifying details properly rejected.")

    # -------------------------------------------------------------------------
    # 4. TEST ADDING STANDARD CAUSE (e.g. Drunk Driving)
    # -------------------------------------------------------------------------
    print("\n--- 4. Testing Adding Accident with Standard Cause ---")
    res_add_std = client.post('/add-accident', data={
        'csrf_token': auth_csrf,
        'accident_datetime': now_str,
        'region': 'Cause Test Sector A',
        'road_name': 'Test Way 1',
        'vehicle_type': 'Car',
        'severity': 'Serious',
        'weather': 'Rainy',
        'cause_of_accident': 'Drunk Driving'
    }, follow_redirects=True)
    assert res_add_std.status_code == 200
    assert 'Accident record added successfully' in res_add_std.data.decode('utf-8')

    # Verify in MySQL
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.accident_id, a.cause_of_accident
        FROM accidents a
        JOIN locations l ON a.location_id = l.location_id
        WHERE l.region = 'Cause Test Sector A'
        ORDER BY a.accident_id DESC LIMIT 1
    """)
    record_std = cur.fetchone()
    cur.close()
    conn.close()
    assert record_std is not None, "Standard cause record not found in MySQL"
    assert record_std['cause_of_accident'] == 'Drunk Driving'
    std_id = record_std['accident_id']
    print(f"  [PASS] Record #{std_id} stored in MySQL with cause='Drunk Driving'.")

    # Verify on /accidents page
    res_view_std = client.get('/accidents')
    assert 'Drunk Driving' in res_view_std.data.decode('utf-8')
    print("  [PASS] 'Drunk Driving' correctly displayed in Accident Records table.")

    # -------------------------------------------------------------------------
    # 5. TEST ADDING CUSTOM CAUSE VIA 'OTHER' (e.g. Brake failure)
    # -------------------------------------------------------------------------
    print("\n--- 5. Testing Adding Accident with Custom 'Other' Cause ---")
    custom_cause_text = "Sudden tire blowout and brake failure"
    res_add_custom = client.post('/add-accident', data={
        'csrf_token': auth_csrf,
        'accident_datetime': now_str,
        'region': 'Cause Test Sector B',
        'road_name': 'Test Way 2',
        'vehicle_type': 'Truck',
        'severity': 'Fatal',
        'weather': 'Foggy',
        'cause_of_accident': 'Other',
        'other_cause': custom_cause_text
    }, follow_redirects=True)
    assert res_add_custom.status_code == 200
    assert 'Accident record added successfully' in res_add_custom.data.decode('utf-8')

    # Verify in MySQL
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.accident_id, a.cause_of_accident
        FROM accidents a
        JOIN locations l ON a.location_id = l.location_id
        WHERE l.region = 'Cause Test Sector B'
        ORDER BY a.accident_id DESC LIMIT 1
    """)
    record_custom = cur.fetchone()
    cur.close()
    conn.close()
    assert record_custom is not None, "Custom cause record not found in MySQL"
    assert record_custom['cause_of_accident'] == custom_cause_text
    custom_id = record_custom['accident_id']
    print(f"  [PASS] Record #{custom_id} stored in MySQL with custom cause='{custom_cause_text}'.")

    # Verify on /accidents page
    res_view_custom = client.get('/accidents')
    assert custom_cause_text in res_view_custom.data.decode('utf-8')
    print(f"  [PASS] Custom cause '{custom_cause_text}' correctly displayed in Accident Records table.")

    # -------------------------------------------------------------------------
    # 6. TEST DELETION OF TEST RECORDS
    # -------------------------------------------------------------------------
    print("\n--- 6. Testing Deletion of Added Records ---")
    res_del1 = client.post(f'/delete-accident/{std_id}', data={'csrf_token': auth_csrf}, follow_redirects=True)
    assert res_del1.status_code == 200
    assert f"Accident record #{std_id} was deleted successfully" in res_del1.data.decode('utf-8')
    print(f"  [PASS] Record #{std_id} successfully deleted.")

    res_del2 = client.post(f'/delete-accident/{custom_id}', data={'csrf_token': auth_csrf}, follow_redirects=True)
    assert res_del2.status_code == 200
    assert f"Accident record #{custom_id} was deleted successfully" in res_del2.data.decode('utf-8')
    print(f"  [PASS] Record #{custom_id} successfully deleted.")

    # -------------------------------------------------------------------------
    # 7. CLEANUP ANY REMAINING TEST LOCATIONS
    # -------------------------------------------------------------------------
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM locations WHERE region IN ('Cause Test Sector A', 'Cause Test Sector B', 'Validation Zone')")
    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 65)
    print("ALL CAUSE OF ACCIDENT TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()

