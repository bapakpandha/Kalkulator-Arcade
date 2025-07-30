from flask import Flask, render_template, request, flash, redirect, url_for
from scrape import fetch_data
from utils import summarize, get_points
from db import update_stats, log_history, get_leaderboard_data, get_progress_data
from werkzeug.middleware.proxy_fix import ProxyFix
from collections import Counter
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

def process_daily_activity(badges):
    if not badges:
        return []
    
    dates = [b[2].strftime('%Y-%m-%d') for b in badges]
    date_counts = Counter(dates)
    chart_data = [{'x': date, 'y': count} for date, count in sorted(date_counts.items())]
    
    return chart_data

@app.context_processor
def inject_helpers():
    return dict(get_points=get_points)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form.get("profile_url", "").strip()
        if not url.startswith("https://www.cloudskillsboost.google/public_profiles/"):
            flash("URL profil yang Anda masukkan tidak valid. Harap gunakan format yang benar.", "danger")
            return redirect(url_for('index'))
        
        try:
            profile_data = fetch_data(url)
            event_badges = profile_data["event_badges"]

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
                                   daily_activity=daily_activity)
        except Exception as e:
            flash(f"Terjadi kesalahan saat mengambil data: {e}", "danger")
    
    return render_template("index.html")

@app.route("/leaderboard")
def leaderboard():
    leaderboard_list = get_leaderboard_data()
    return render_template("leaderboard.html", leaders=leaderboard_list)

if __name__ == "__main__":
    app.run(debug=False, host='127.0.0.1', port=58394)