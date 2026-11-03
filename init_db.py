import os
from werkzeug.security import generate_password_hash
from database import get_connection

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def init_database():
    """
    Initializes database tables and default administrator on application startup.
    Ensures zero-setup compatibility for Railway cloud deployments and local environments.
    """
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # 1. Create locations table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id INT AUTO_INCREMENT PRIMARY KEY,
                region VARCHAR(100) NOT NULL,
                road_name VARCHAR(150) DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        connection.commit()

        # 2. Create accidents table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accidents (
                accident_id INT AUTO_INCREMENT PRIMARY KEY,
                accident_datetime DATETIME NOT NULL,
                location_id INT NOT NULL,
                vehicle_type VARCHAR(50) NOT NULL,
                severity VARCHAR(30) NOT NULL,
                weather VARCHAR(50) DEFAULT NULL,
                cause_of_accident VARCHAR(255) NOT NULL DEFAULT 'Not Specified',
                FOREIGN KEY (location_id) REFERENCES locations(location_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        connection.commit()

        # 3. Create users table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        connection.commit()
        print("Database tables ('locations', 'accidents', 'users') verified.")

        # 4. Check if admin user exists; create default if table is empty
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()["count"]

        if user_count == 0:
            default_user = os.environ.get("ADMIN_USERNAME", "admin")
            default_pass = os.environ.get("ADMIN_PASSWORD", "Admin@123")
            pw_hash = generate_password_hash(default_pass)

            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (default_user, pw_hash)
            )
            connection.commit()
            print(f"Default admin user created: username='{default_user}'")
        else:
            print(f"Users table already contains {user_count} account(s).")

        # 5. Check if locations/accidents are empty (fresh Railway deploy); seed initial baseline if empty
        cursor.execute("SELECT COUNT(*) as count FROM locations")
        loc_count = cursor.fetchone()["count"]

        if loc_count == 0:
            print("Fresh database detected: Seeding baseline locations and accident records...")
            initial_locations = [
                (1, "Tirupati", "Gandhi Road"),
                (2, "Banglore", "JP Ngaar"),
                (3, "kadapa", "SV Road"),
                (4, "Tirupati", None),
                (5, "Tirupati", "Sai Nagar")
            ]
            cursor.executemany(
                "INSERT INTO locations (location_id, region, road_name) VALUES (%s, %s, %s)",
                initial_locations
            )
            connection.commit()

            initial_accidents = [
                (1, "2026-10-26 23:08:00", 1, "Bike", "Minor", "Rainy", "Not Specified"),
                (2, "2026-10-08 01:03:00", 2, "Car", "Fatal", "Other", "Not Specified"),
                (3, "2026-06-18 19:40:00", 3, "Truck", "Serious", "Clear", "Not Specified"),
                (4, "2026-10-14 21:02:00", 4, "Car", "Minor", "Foggy", "Not Specified"),
                (5, "2026-01-16 22:46:00", 5, "Auto", "Serious", "Other", "Not Specified")
            ]
            cursor.executemany("""
                INSERT INTO accidents
                    (accident_id, accident_datetime, location_id, vehicle_type, severity, weather, cause_of_accident)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, initial_accidents)
            connection.commit()
            print("Baseline dataset seeded successfully.")

        # 6. Verify cause_of_accident column exists on accidents table
        cursor.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'accidents'
              AND COLUMN_NAME = 'cause_of_accident'
        """)
        column_exists = cursor.fetchone()

        if not column_exists:
            cursor.execute("""
                ALTER TABLE accidents
                ADD COLUMN cause_of_accident VARCHAR(255) NOT NULL DEFAULT 'Not Specified';
            """)
            connection.commit()
            print("Column 'cause_of_accident' added to 'accidents' table.")

        # Ensure all existing records have 'Not Specified' instead of NULL or blank
        cursor.execute("""
            UPDATE accidents
            SET cause_of_accident = 'Not Specified'
            WHERE cause_of_accident IS NULL OR cause_of_accident = '';
        """)
        connection.commit()

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    init_database()
