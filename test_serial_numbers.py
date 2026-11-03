"""
Verification script for S.No. (Serial Number) display and Delete functionality
in Road Accident Data Analysis System.
"""
import sys
from bs4 import BeautifulSoup
from app import app
from database import get_connection

def run_tests():
    print("=" * 65)
    print("TESTING ACCIDENT RECORDS S.NO. & RECORD INTEGRITY")
    print("=" * 65)

    client = app.test_client()

    # 1. Login with admin credentials
    res_login_page = client.get('/login')
    html_login = res_login_page.data.decode('utf-8')
    soup_login = BeautifulSoup(html_login, 'html.parser')
    csrf_token = soup_login.find('input', {'name': 'csrf_token'})['value']

    res_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'username': 'admin',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res_login.status_code == 200, f"Login failed: status {res_login.status_code}"

    # 2. Fetch /accidents and inspect HTML
    print("\n--- 1. Testing S.No. & Accident ID display on /accidents ---")
    res = client.get("/accidents")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    html = res.data.decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    assert table is not None, "Accident records table not found in HTML"

    headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
    print(f"  Table headers found: {headers}")
    assert "S.No." in headers, "Missing 'S.No.' column header"
    assert "Accident ID" in headers, "Missing 'Accident ID' column header"
    print("  [PASS] 'S.No.' and 'Accident ID' headers are present in table.")

    rows = table.find("tbody").find_all("tr")
    print(f"  Total records displayed: {len(rows)}")

    snos = []
    db_ids = []
    for r in rows:
        tds = r.find_all("td")
        if len(tds) >= 8:
            snos.append(int(tds[0].get_text(strip=True)))
            db_ids.append(tds[1].get_text(strip=True))

    print(f"  Rendered S.No. values: {snos}")
    print(f"  Rendered Accident ID values: {db_ids}")

    # Verify sequential S.No. starting from 1
    expected_snos = list(range(1, len(rows) + 1))
    assert snos == expected_snos, f"Serial numbers are not sequential! Expected {expected_snos}, got {snos}"
    print(f"  [PASS] Serial numbers appear strictly sequentially: {snos}")

    # Verify MySQL database original IDs match
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT a.accident_id
        FROM accidents a
        JOIN locations l ON a.location_id = l.location_id
        ORDER BY a.accident_datetime DESC
    """)
    db_records = cur.fetchall()
    cur.close()
    conn.close()

    expected_db_ids = [f"#{r['accident_id']}" for r in db_records]
    assert db_ids == expected_db_ids, f"Database IDs mismatch! Expected {expected_db_ids}, got {db_ids}"
    print(f"  [PASS] Original database IDs match MySQL database exactly: {expected_db_ids}")

    # 3. Test Adding a new record and verifying sequential S.No.
    print("\n--- 2. Testing Adding New Accident & S.No. update ---")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT location_id FROM locations LIMIT 1")
    loc_id = cur.fetchone()["location_id"]

    # Insert a temporary test record with datetime in future so it becomes row #1
    cur.execute("""
        INSERT INTO accidents (accident_datetime, location_id, vehicle_type, severity, weather)
        VALUES ('2099-01-01 12:00:00', %s, 'Car', 'Minor', 'Clear')
    """, (loc_id,))
    conn.commit()
    temp_id = cur.lastrowid
    cur.close()
    conn.close()
    print(f"  Created temporary test record with MySQL ID: #{temp_id}")

    try:
        res = client.get("/accidents")
        soup = BeautifulSoup(res.data.decode("utf-8"), "html.parser")
        new_rows = soup.find("table").find("tbody").find_all("tr")
        new_snos = [int(r.find_all("td")[0].get_text(strip=True)) for r in new_rows]
        new_first_id = new_rows[0].find_all("td")[1].get_text(strip=True)

        assert new_snos == list(range(1, len(new_rows) + 1)), f"S.No. not sequential after add: {new_snos}"
        assert new_first_id == f"#{temp_id}", f"Expected first record to be #{temp_id}, got {new_first_id}"
        print(f"  [PASS] After addition, new record is S.No. 1 with ID #{temp_id}, and all S.No. remain sequential: {new_snos}")

        # 4. Test Deletion using original accident ID
        print("\n--- 3. Testing Deletion using original accident ID ---")
        # Get active csrf token from session
        with client.session_transaction() as sess:
            auth_csrf = sess["csrf_token"]

        res_del = client.post(f"/delete-accident/{temp_id}", data={"csrf_token": auth_csrf}, follow_redirects=True)
        assert res_del.status_code == 200
        assert f"Accident record #{temp_id} was deleted successfully" in res_del.data.decode("utf-8")
        print(f"  [PASS] Delete endpoint correctly deleted record #{temp_id}.")

        # Verify record is gone from DB
        conn = get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM accidents WHERE accident_id = %s", (temp_id,))
        assert cur.fetchone() is None, "Record still exists in MySQL after deletion!"
        cur.close()
        conn.close()
        print(f"  [PASS] Verified record #{temp_id} is completely removed from MySQL.")

        # Re-verify S.No. after deletion
        res = client.get("/accidents")
        soup = BeautifulSoup(res.data.decode("utf-8"), "html.parser")
        post_del_rows = soup.find("table").find("tbody").find_all("tr")
        post_snos = [int(r.find_all("td")[0].get_text(strip=True)) for r in post_del_rows]
        assert post_snos == list(range(1, len(post_del_rows) + 1)), f"S.No. not sequential after delete: {post_snos}"
        print(f"  [PASS] After deletion, S.No. seamlessly restored to sequential: {post_snos}")

    finally:
        # Guarantee cleanup if anything failed
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM accidents WHERE accident_id = %s", (temp_id,))
        conn.commit()
        cur.close()
        conn.close()

    print("\n" + "=" * 65)
    print("ALL TESTS PASSED! S.NO. IMPLEMENTATION IS 100% VERIFIED.")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
