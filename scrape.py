import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dt
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any

START_DATE = datetime(2025, 7, 15, tzinfo=timezone.utc)
Badge = Tuple[str, str, datetime]
COURSE_BADGE = {
    "Work with Gemini Models in BigQuery", "Responsible AI for Developers: Privacy & Safety",
    "Advanced ML: ML Infrastructure", "Intermediate ML: TensorFlow on Google Cloud",
    "Workspace: Add-ons", "Modernizing Retail and Ecommerce Solutions with Google Cloud",
    "Machine Learning in the Enterprise", "Google Developer Essentials",
    "Google Cloud Computing Foundations: Data, ML, and AI in Google Cloud",
    "Gemini for Data Scientists and Analysts", "Boost Productivity with Gemini in BigQuery",
    "Achieving Advanced Insights with BigQuery",
    "Machine Learning Operations (MLOps) for Generative AI",
    "Machine Learning Operations (MLOps) with Vertex AI: Model Evaluation",
}
EXCLUDED_COURSE = {" ".join(course.lower().split()) for course in COURSE_BADGE}

def fetch_data(profile_url: str) -> Dict[str, Any]:
    """Mengambil data profil lengkap termasuk info profil, liga, dan badge event."""
    resp = requests.get(profile_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    name_tag = soup.select_one("h1.ql-display-small")
    member_since_tag = soup.select_one("p.ql-body-large.l-mbl")
    avatar_tag = soup.select_one("ql-avatar.profile-avatar")
    
    league_container = soup.select_one("div.profile-league")
    league_name = "N/A"
    league_points = 0
    league_icon_url = ""

    if league_container:
        name_tag_league = league_container.select_one("h2.ql-headline-medium")
        points_tag = league_container.select_one("strong")
        icon_tag = league_container.select_one("img")

        if name_tag_league:
            league_name = name_tag_league.get_text(strip=True)
        if points_tag:
            points_text = points_tag.get_text(strip=True).replace(" points", "").replace(",", "")
            league_points = int(points_text) if points_text.isdigit() else 0
        if icon_tag and icon_tag.has_attr('src'):
            league_icon_url = icon_tag['src']

    profile_summary = {
        "name": name_tag.get_text(strip=True) if name_tag else "Anonymous",
        "member_since": member_since_tag.get_text(strip=True) if member_since_tag else "N/A",
        "photo_url": avatar_tag['src'] if avatar_tag and avatar_tag.has_attr('src') else None,
        "league_name": league_name,
        "league_points": league_points,
        "league_icon_url": league_icon_url
    }

    cards = soup.select("div.profile-badge")
    dialogs = {dlg["id"]: dlg for dlg in soup.select("ql-dialog[id]")}
    
    event_badges: List[Badge] = []
    for card in cards:
        title_el = card.select_one("span.ql-title-medium")
        date_el = card.select_one("span.ql-body-medium")

        if not (title_el and date_el):
            continue

        badge_name = title_el.get_text(strip=True)
        normalized_name = " ".join(badge_name.lower().split())
        if normalized_name in EXCLUDED_COURSE:
            continue

        m = re.search(r"([A-Za-z]{3}\s+\d{1,2},\s+\d{4})", date_el.get_text())
        if not m:
            continue
        date_obj = dt.parse(m.group(1)).replace(tzinfo=timezone.utc)
        if date_obj < START_DATE:
            continue

        nl = badge_name.lower()
        tipe = None
        if "extra" in nl: tipe = "extra"
        elif "trivia" in nl: tipe = "trivia"
        elif "level" in nl: tipe = "arcade"

        modal_button = card.select_one("ql-button[modal]")
        modal_id = modal_button["modal"] if modal_button else None
        if not tipe and modal_id and modal_id in dialogs:
            dlg = dialogs.get(modal_id)
            btn = dlg.select_one("ql-button[href]") if dlg else None
            href = btn["href"].strip() if btn and btn.has_attr("href") else ""
            if href.startswith("/games/"):
                hl = (dlg.get("headline", "") or "").lower() if dlg else ""
                tipe = "trivia" if "trivia" in nl or "trivia" in hl else "arcade"

        if not tipe: tipe = "skill"
        event_badges.append((badge_name, tipe, date_obj))

    profile_summary['event_badges'] = sorted(event_badges, key=lambda item: item[2], reverse=True)
    return profile_summary