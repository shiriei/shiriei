import os
import json
import urllib.request
import urllib.error
import math
from datetime import datetime
from collections import defaultdict

def fetch_contributions(username, token):
    url = "https://api.github.com/graphql"
    query = """
    query {
      user(login: "%s") {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """ % username

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            if "errors" in result:
                print("GraphQL Errors:", result["errors"])
                return None
                
            user_data = result.get("data", {}).get("user")
            if not user_data:
                print("User not found or no data returned.")
                return None
                
            return user_data["contributionsCollection"]["contributionCalendar"]
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}")
        return None

def draw_star(cx, cy, r, opacity=1.0):
    # Generates an elegant 4-point sparkle using SVG Bezier curves (Q)
    return f'<path d="M {cx:.1f} {cy-r:.1f} Q {cx:.1f} {cy:.1f} {cx+r:.1f} {cy:.1f} Q {cx:.1f} {cy:.1f} {cx:.1f} {cy+r:.1f} Q {cx:.1f} {cy:.1f} {cx-r:.1f} {cy:.1f} Q {cx:.1f} {cy:.1f} {cx:.1f} {cy-r:.1f} Z" fill="#39FFDF" fill-opacity="{opacity:.2f}" />'

def generate_svg(calendar_data, filepath, width=1200, height=600):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except OSError as e:
        print(f"Filesystem error creating directory: {e}")
        return

    weeks = calendar_data.get("weeks", [])
    total_contributions = calendar_data.get("totalContributions", 0)
    
    all_days = []
    for week in weeks:
        for day in week.get("contributionDays", []):
            all_days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })
            
    if not all_days:
        print("No days found in calendar.")
        return
        
    # Calculate Statistics
    longest_streak = 0
    current_streak = 0
    month_counts = defaultdict(int)
    
    for d in all_days:
        if d["count"] > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
            
        month = d["date"][0:7]
        month_counts[month] += d["count"]
        
    active_days = sum(1 for d in all_days if d["count"] > 0)
    
    most_active_month = "N/A"
    if month_counts:
        best_month_str = max(month_counts.items(), key=lambda x: x[1])[0]
        try:
            dt = datetime.strptime(best_month_str, "%Y-%m")
            most_active_month = dt.strftime("%b %Y")
        except ValueError:
            most_active_month = best_month_str

    # Prepare nodes for active contribution stars
    active_nodes = []
    month_labels = []
    last_month = None
    
    total_days = len(all_days)
    for i, d in enumerate(all_days):
        x = 100 + (i / max(1, total_days - 1)) * 1000
        # Underlying timeline base for vertical scattering
        base_y = 260 + math.sin(i / 15.0) * 80 + math.cos(i / 7.0) * 30
        
        # Record month label positions
        month_str = d["date"][5:7]
        if month_str != last_month:
            try:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                month_name = dt.strftime("%b")
                if x > 120 or not month_labels:
                    month_labels.append({"x": x, "label": month_name})
            except ValueError:
                pass
            last_month = month_str
            
        if d["count"] > 0:
            # Find a safe vertical position to prevent star overlap
            lane_offsets = [0, 50, -50, 100, -100, 150, -150]
            safe_y = base_y
            for offset in lane_offsets:
                test_y = base_y + offset
                overlap = False
                for p in reversed(active_nodes[-15:]):
                    dx = abs(p["x"] - x)
                    dy = abs(p["y"] - test_y)
                    # Vertical separation needed for text labels
                    if dx < 40 and dy < 60:
                        overlap = True
                        break
                if not overlap:
                    safe_y = test_y
                    break
                    
            active_nodes.append({
                "index": i,
                "x": x,
                "y": safe_y,
                "count": d["count"],
                "date": d["date"]
            })

    # Prepare deterministic decorative background stars
    background_stars = []
    for i in range(70):
        # Pseudo-random but deterministic properties
        bx = 50 + ((i * 137) % 1100)
        by = 120 + ((i * 93) % 300)
        br = 0.5 + ((i * 17) % 2)
        opacity = 0.05 + ((i * 11) % 20) / 100.0
        background_stars.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{br:.1f}" fill="#39FFDF" fill-opacity="{opacity:.2f}"/>')

    # Build SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '  <style>',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }',
        '  </style>',
        f'  <rect width="{width}" height="{height}" fill="#0d1117" rx="15" />'
    ]
    
    # Title & Subtitle
    svg.append('  <text x="100" y="60" fill="#c9d1d9" font-size="28" font-weight="bold">Contribution Constellation</text>')
    svg.append('  <text x="100" y="90" fill="#8b949e" font-size="16">GitHub activity &#8226; Last 12 months</text>')
    
    # Legend
    svg.append('  <g transform="translate(800, 70)">')
    svg.append('    <text x="0" y="0" fill="#8b949e" font-size="14">Contribution intensity</text>')
    svg.append('    <text x="160" y="0" fill="#8b949e" font-size="12">Less</text>')
    svg.append('    <circle cx="200" cy="-4" r="2" fill="#39FFDF" fill-opacity="0.3"/>')
    svg.append('    ' + draw_star(225, -4, 4, 0.5))
    svg.append('    ' + draw_star(250, -4, 6, 0.7))
    svg.append('    ' + draw_star(275, -4, 8, 0.9))
    svg.append('    ' + draw_star(300, -4, 10, 1.0))
    svg.append('    <text x="320" y="0" fill="#8b949e" font-size="12">More</text>')
    svg.append('  </g>')

    # Decorative Background
    svg.append('  <g id="background-stars">')
    for star_str in background_stars:
        svg.append(f'    {star_str}')
    svg.append('  </g>')
    
    # Month Timeline (Subtle timeline at bottom)
    svg.append('  <g id="timeline">')
    svg.append('    <line x1="100" y1="440" x2="1100" y2="440" stroke="#30363d" stroke-width="1" />')
    for m in month_labels:
        svg.append(f'  <text x="{m["x"]:.1f}" y="458" fill="#8b949e" font-size="12" text-anchor="middle">{m["label"]}</text>')
    svg.append('  </g>')

    # Primary Contribution Stars
    svg.append('  <g id="contribution-stars">')
    for n in active_nodes:
        count = n["count"]
        
        # Scaling logic: smaller stars for 1-5, escalating rapidly for 11+
        if count <= 2:
            r = 5.0 + count * 0.5
        elif count <= 5:
            r = 7.0 + (count - 2) * 1.0
        elif count <= 10:
            r = 10.0 + (count - 5) * 1.0
        else:
            r = 15.0 + math.log1p(count - 10) * 3.0
            
        opacity = min(1.0, 0.4 + math.log1p(count) * 0.2)
        glow_r = r * 1.6
        
        # Subtle radial glow behind the star
        svg.append(f'    <circle cx="{n["x"]:.1f}" cy="{n["y"]:.1f}" r="{glow_r:.1f}" fill="#39FFDF" fill-opacity="{opacity * 0.15:.2f}"/>')
        
        # The star shape itself
        svg.append('    ' + draw_star(n["x"], n["y"], r, opacity))
        
        # Text label for exact contribution count
        svg.append(f'    <text x="{n["x"]:.1f}" y="{n["y"] - r - 6:.1f}" fill="#ffffff" font-size="12" font-weight="bold" text-anchor="middle">{count}</text>')
        
        # Text label for exact date
        try:
            dt = datetime.strptime(n["date"], "%Y-%m-%d")
            date_str = dt.strftime("%b %d")
        except ValueError:
            date_str = n["date"][5:]
        svg.append(f'    <text x="{n["x"]:.1f}" y="{n["y"] + r + 14:.1f}" fill="#8b949e" font-size="10" text-anchor="middle">{date_str}</text>')
    svg.append('  </g>')

    # Summary Statistics Cards
    stats_y = 480
    card_width = 220
    card_height = 80
    spacing = (1000 - 4 * card_width) / 3
    stats = [
        ("Total Contributions", str(total_contributions)),
        ("Active Days", str(active_days)),
        ("Longest Streak", f"{longest_streak} days"),
        ("Most Active Month", most_active_month)
    ]
    
    for idx, (title, value) in enumerate(stats):
        cx = 100 + idx * (card_width + spacing)
        svg.append(f'  <rect x="{cx}" y="{stats_y}" width="{card_width}" height="{card_height}" rx="8" fill="#161b22" stroke="#30363d"/>')
        svg.append(f'  <text x="{cx + card_width/2}" y="{stats_y + 30}" fill="#8b949e" font-size="14" text-anchor="middle">{title}</text>')
        # Teal accent color instead of pink
        svg.append(f'  <text x="{cx + card_width/2}" y="{stats_y + 60}" fill="#39FFDF" font-size="22" font-weight="bold" text-anchor="middle">{value}</text>')

    svg.append('</svg>')
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(svg))
    except OSError as e:
        print(f"Filesystem error writing SVG file: {e}")

def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("GH_TOKEN environment variable not found. Please set it to a valid GitHub token.")
        return
        
    username = "shiriei"
    print(f"Fetching contributions for {username}...")
    calendar_data = fetch_contributions(username, token)
    
    if not calendar_data:
        print("No contribution data found or error occurred.")
        return
        
    print("Generating network visualization...")
    output_file = os.path.join("output", "contribution-network.svg")
    generate_svg(calendar_data, output_file)
    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    main()
