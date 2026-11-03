import argparse
import getpass
from werkzeug.security import generate_password_hash
from database import get_connection

def create_or_update_user(username, password):
    if not username or not password:
        print("Error: Username and password must not be empty.")
        return False

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        pw_hash = generate_password_hash(password)
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (pw_hash, existing["user_id"])
            )
            print(f"Password for existing user '{username}' has been updated.")
        else:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, pw_hash)
            )
            print(f"New user '{username}' has been created successfully.")

        connection.commit()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update an administrator account.")
    parser.add_argument("--username", help="Username for the administrator")
    parser.add_argument("--password", help="Password for the administrator")
    args = parser.parse_args()

    user = args.username or input("Enter username: ").strip()
    pwd = args.password or getpass.getpass("Enter password: ")

    create_or_update_user(user, pwd)

