from collections import Counter
from typing import List, Dict, Optional, Tuple, Any
from scrape import Badge

POINTS = {"arcade": 1.0, "trivia": 1.0, "skill": 0.5, "extra": 2.0}
MILESTONES_DATA: List[Dict[str, Any]] = [
    {
        "name": "Milestone 1",
        "reqs": {"arcade": 4, "trivia": 4, "skill": 10},
        "bonus": 5,
        "icon": "fa-medal",
        "color": "#6c757d"
    },
    {
        "name": "Milestone 2",
        "reqs": {"arcade": 6, "trivia": 6, "skill": 20},
        "bonus": 10,
        "icon": "fa-award",
        "color": "#007bff"
    },
    {
        "name": "Milestone 3",
        "reqs": {"arcade": 8, "trivia": 7, "skill": 30},
        "bonus": 15,
        "icon": "fa-trophy",
        "color": "#ffc107"
    },
    {
        "name": "Ultimate Milestone",
        "reqs": {"arcade": 10, "trivia": 8, "skill": 44},
        "bonus": 25,
        "icon": "fa-crown",
        "color": "#8a2be2"
    }
]

def determine_milestone(counts: Counter) -> Tuple[Optional[str], int]:
    highest_milestone = None
    bonus = 0
    for m in MILESTONES_DATA:
        if all(counts.get(k, 0) >= v for k, v in m["reqs"].items()):
            highest_milestone = m["name"]
            bonus = m["bonus"]
    return highest_milestone, bonus

def summarize(badges: List[Badge]) -> Dict:
    cnt = Counter(b[1] for b in badges)
    base = sum(cnt.get(t, 0) * POINTS.get(t, 0) for t in POINTS)
    milestone_counts = cnt.copy()
    milestone_counts['arcade'] += milestone_counts.get('extra', 0)
    milestone_name, bonus = determine_milestone(milestone_counts)
    total_points = base + bonus
    milestone_progress = []
    for m in MILESTONES_DATA:
        progress_data = {
            "name": m["name"],
            "bonus_points": m["bonus"],
            "icon": m["icon"],
            "color": m["color"],
            "reqs": m["reqs"],
            "is_complete": all(milestone_counts.get(k, 0) >= v for k, v in m["reqs"].items())
        }
        arcade_progress_val = milestone_counts.get("arcade", 0)
        progress_data["progress"] = {
            "arcade": {
                "current": arcade_progress_val,
                "required": m["reqs"]["arcade"],
                "percentage": min(100, (arcade_progress_val / m["reqs"]["arcade"]) * 100) if m["reqs"]["arcade"] > 0 else 100
            },
            "trivia": {
                "current": milestone_counts.get("trivia", 0),
                "required": m["reqs"]["trivia"],
                "percentage": min(100, (milestone_counts.get("trivia", 0) / m["reqs"]["trivia"]) * 100) if m["reqs"]["trivia"] > 0 else 100
            },
            "skill": {
                "current": milestone_counts.get("skill", 0),
                "required": m["reqs"]["skill"],
                "percentage": min(100, (milestone_counts.get("skill", 0) / m["reqs"]["skill"]) * 100) if m["reqs"]["skill"] > 0 else 100
            }
        }
        milestone_progress.append(progress_data)

    chart_counts = [cnt.get("arcade", 0), cnt.get("trivia", 0), cnt.get("skill", 0), cnt.get("extra", 0)]
    chart_points = [round(c * p, 1) for c, p in zip(chart_counts, [POINTS['arcade'], POINTS['trivia'], POINTS['skill'], POINTS['extra']])]

    return {
        "counts": cnt,
        "points_base": base,
        "milestone": milestone_name or "Belum ada",
        "points_bonus": bonus,
        "points_total": total_points,
        "chart_counts": chart_counts,
        "chart_points": chart_points,
        "milestone_progress": milestone_progress
    }

def get_points() -> Dict:
    return POINTS
