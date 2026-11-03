from database import get_connection

try:
    connection = get_connection()

    if connection.is_connected():
        print("MySQL connected successfully!")
        print("Database: road_accident_db")

    connection.close()

except Exception as e:
    print("Connection failed:", e)