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

def update_stats(score, profile_url, photo_url, name, ip):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    stat_id = None
    try:
        cursor.execute("SELECT id FROM stats WHERE profile_url = %s", (profile_url,))
        result = cursor.fetchone()

        if result:
            stat_id = result[0]
            query = """
                UPDATE stats 
                SET score = %s, photo_url = %s, name = %s, last_check = NOW(), ip = %s
                WHERE id = %s
            """
            cursor.execute(query, (score, photo_url, name, ip, stat_id))
        else:
            query = """
                INSERT INTO stats (score, profile_url, photo_url, name, last_check, ip)
                VALUES (%s, %s, %s, %s, NOW(), %s)
            """
            cursor.execute(query, (score, profile_url, photo_url, name, ip))
            stat_id = cursor.lastrowid
        
        conn.commit()
        return stat_id
    except Error as e:
        print(f"Database error on update_stats: {e}")
        conn.rollback()
        return None
    finally:
        cursor.close()
        conn.close()

def log_history(stat_id, score):
    if not stat_id:
        return
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        query = "INSERT INTO history (stat_id, score, check_time) VALUES (%s, %s, NOW())"
        cursor.execute(query, (stat_id, score))
        conn.commit()
    except Error as e:
        print(f"Database error on log_history: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_leaderboard_data():
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT name, score, photo_url FROM stats ORDER BY score DESC LIMIT 20"
        cursor.execute(query)
        return cursor.fetchall()
    except Error as e:
        print(f"Database error on get_leaderboard_data: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_progress_data(stat_id):
    conn = get_db_connection()
    if not conn:
        return {'daily': [], 'weekly': [], 'user': None}
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, profile_url, photo_url FROM stats WHERE id = %s", (stat_id,))
        user_info = cursor.fetchone()

        query_daily = """
            SELECT DATE(check_time) AS date, MAX(score) AS score
            FROM history
            WHERE stat_id = %s AND check_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(check_time)
            ORDER BY date;
        """
        cursor.execute(query_daily, (stat_id,))
        daily_data = cursor.fetchall()

        query_weekly = """
            SELECT YEARWEEK(check_time, 1) as week, MAX(score) AS score
            FROM history
            WHERE stat_id = %s
            GROUP BY week
            ORDER BY week;
        """
        cursor.execute(query_weekly, (stat_id,))
        weekly_data = cursor.fetchall()
        
        return {'daily': daily_data, 'weekly': weekly_data, 'user': user_info}

    except Error as e:
        print(f"Database error on get_progress_data: {e}")
        return {'daily': [], 'weekly': [], 'user': None}
    finally:
        cursor.close()
        conn.close()