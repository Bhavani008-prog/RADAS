import os
from urllib.parse import urlparse
import mysql.connector

# Load local environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_connection():
    """
    Establishes a MySQL database connection compatible with both local
    development and Railway cloud deployment.
    """
    # 1. Check for complete connection URL (Railway provides MYSQL_URL or DATABASE_URL)
    db_url = os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("mysql"):
        parsed = urlparse(db_url)
        return mysql.connector.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 3306,
            user=parsed.username or "root",
            password=parsed.password or "",
            database=parsed.path.lstrip("/") or "road_accident_db"
        )

    # 2. Check for individual environment variables (Railway or custom .env)
    host = os.environ.get("MYSQLHOST") or os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("MYSQLPORT") or os.environ.get("DB_PORT", 3306))
    user = os.environ.get("MYSQLUSER") or os.environ.get("DB_USER", "root")
    password = os.environ.get("MYSQLPASSWORD") or os.environ.get("DB_PASSWORD", "")
    database = os.environ.get("MYSQLDATABASE") or os.environ.get("DB_NAME", "road_accident_db")

    return mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
