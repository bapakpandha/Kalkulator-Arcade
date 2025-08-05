from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from scrape import fetch_data, load_valid_skill_badges
from utils import summarize, get_points, calculate_simulation, calculate_needed_badges
from db import update_stats, log_history, get_leaderboard_data
from werkzeug.middleware.proxy_fix import ProxyFix
from collections import Counter
from functools import wraps
from datetime import datetime
import os
import json
import maxminddb

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

LOG_FILE = 'accessip.txt'

def log_ip_access(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} - {message}\n")
    except Exception as e:
        print(f"Gagal menulis ke file log: {e}")

ALLOWED_COUNTRIES = {'ID', 'SG'}
GEOIP_DATABASE = 'database.mmdb'

def check_ip_location_local(ip):
    if ip == '127.0.0.1':
        log_ip_access(f"IP {ip} - Akses dari localhost, diizinkan.")
        return True

    try:
        with maxminddb.open_database(GEOIP_DATABASE) as reader:
            data = reader.get(ip)
            if data and 'country_code' in data:
                country_code = data['country_code']
                is_allowed = country_code in ALLOWED_COUNTRIES
                status = "DIIZINKAN" if is_allowed else "DITOLAK"
                log_ip_access(f"IP {ip} - Terdeteksi dari negara: {country_code} - Status: {status}")
                return is_allowed
            else:
                log_ip_access(f"IP {ip} - 'country_code' tidak ditemukan - Status: DITOLAK")
                return False
    except FileNotFoundError:
        log_ip_access(f"IP {ip} - GAGAL: File database '{GEOIP_DATABASE}' tidak ditemukan.")
        return False
    except Exception as e:
        log_ip_access(f"IP {ip} - Terjadi error saat validasi: {e}")
        return False

def ip_check_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_ip_location_local(request.remote_addr):
            return render_template("access_denied.html"), 403
        return f(*args, **kwargs)
    return decorated_function

def process_daily_activity(badges):
    if not badges: return []
    dates = [b[2].strftime('%Y-%m-%d') for b in badges]
    date_counts = Counter(dates)
    return [{'x': date, 'y': count} for date, count in sorted(date_counts.items())]

@app.context_processor
def inject_helpers():
    return dict(get_points=get_points, request=request)

@app.route("/", methods=["GET", "POST"])
@ip_check_required
def index():
    if request.method == "POST":
        url = request.form.get("profile_url", "").strip()
        if not url.startswith("https://www.cloudskillsboost.google/public_profiles/"):
            flash("URL profil tidak valid.", "danger")
            return redirect(url_for('index'))
        try:
            profile_data = fetch_data(url)
            event_badges = profile_data["event_badges"]
            all_skill_badges = load_valid_skill_badges()
            claimed_badge_names = { " ".join(name.lower().split()) for name, tipe, date in profile_data['event_badges'] if tipe == 'skill' }
            unclaimed_badges = [ badge for badge in all_skill_badges if " ".join(badge['name'].lower().split()) not in claimed_badge_names ]
            if not event_badges:
                flash("Tidak ada badge event yang ditemukan atau profil bersifat pribadi.", "warning")
                return render_template("index.html")
            arcade_summary = summarize(event_badges)
            daily_activity = process_daily_activity(event_badges)
            ip_addr = request.remote_addr
            stat_id = update_stats(
                score=arcade_summary['points_total'],
                profile_url=url,
                photo_url=profile_data['photo_url'],
                name=profile_data['name'],
                ip=ip_addr
            )
            if stat_id:
                log_history(stat_id, arcade_summary['points_total'])
            return render_template("result.html",
                                   stat_id=stat_id,
                                   profile_summary=profile_data,
                                   arcade_summary=arcade_summary,
                                   daily_activity=daily_activity,
                                   unclaimed_badges=unclaimed_badges)
        except Exception as e:
            flash(f"Terjadi kesalahan: {e}", "danger")
    return render_template("index.html")

@app.route("/leaderboard")
@ip_check_required
def leaderboard():
    leaderboard_list = get_leaderboard_data()
    return render_template("leaderboard.html", leaders=leaderboard_list)

@app.route("/skill-badges")
@ip_check_required
def skill_badges():
    try:
        with open('skill.json', 'r', encoding='utf-8') as f:
            badges_data = json.load(f)
        sorted_badges = sorted(badges_data, key=lambda x: x['name'])
        return render_template("skill_badges.html", badges=sorted_badges)
    except Exception as e:
        flash(f"Gagal memuat daftar skill badge: {e}", "danger")
        return redirect(url_for('index'))

@app.route("/fast-track")
@ip_check_required
def fast_track():
    try:
        with open('fasttrack.json', 'r', encoding='utf-8') as f:
            fasttrack_data = json.load(f)
        sorted_data = sorted(fasttrack_data, key=lambda x: x['name'])
        return render_template("fasttrack.html", fasttracks=sorted_data)
    except Exception as e:
        flash(f"Gagal memuat daftar Fast Track: {e}", "danger")
        return redirect(url_for('index'))

@app.route("/simulator", methods=["GET", "POST"])
@ip_check_required
def simulator():
    if request.method == 'POST':
        sim_type = request.form.get('sim_type')

        if sim_type == 'calculate_points':
            try:
                arcade = int(request.form.get('arcade', 0))
                trivia = int(request.form.get('trivia', 0))
                skill = int(request.form.get('skill', 0))
                result = calculate_simulation(arcade, trivia, skill)
                return jsonify(result)
            except (ValueError, TypeError):
                return jsonify({"error": "Input harus berupa angka."}), 400

        elif sim_type == 'calculate_badges':
            try:
                target_score = float(request.form.get('target_score', 0))
                arcade = int(request.form.get('arcade_base', 0))
                trivia = int(request.form.get('trivia_base', 0))
                result = calculate_needed_badges(target_score, arcade, trivia)
                return jsonify(result)
            except (ValueError, TypeError):
                return jsonify({"error": "Input harus berupa angka."}), 400

    return render_template("simulator.html")

@app.route("/easy-sb")
@ip_check_required
def easy_sb():
    try:
        with open('easysb.json', 'r', encoding='utf-8') as f:
            easysb_data = json.load(f)
        sorted_data = sorted(easysb_data, key=lambda x: x['name'])
        return render_template("easysb.html", easysb_items=sorted_data)
    except Exception as e:
        flash(f"Gagal memuat daftar Easy SB: {e}", "danger")
        return redirect(url_for('index'))

@app.route("/arcade-triva")
@ip_check_required
def arcade_triva():
    try:
        with open('arcade_triva.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return render_template("arcade_triva.html", items=data)
    except Exception as e:
        flash(f"Gagal memuat daftar Arcade & Triva: {e}", "danger")
        return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=False, host='127.0.0.1')
