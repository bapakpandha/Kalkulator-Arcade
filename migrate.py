import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', 3306),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS')
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

def migrate():
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        # Tabel stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                score INT NOT NULL,
                profile_url VARCHAR(255) NOT NULL UNIQUE,
                photo_url VARCHAR(255),
                name VARCHAR(255),
                last_check DATETIME,
                ip VARCHAR(45)
            )
        """)

        # Tabel history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stat_id INT NOT NULL,
                score INT NOT NULL,
                check_time DATETIME NOT NULL,
                FOREIGN KEY (stat_id) REFERENCES stats(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        print("Migration completed successfully.")
    except Error as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
