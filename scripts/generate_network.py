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

def draw_star(cx, cy, r, fill="#C084FC", opacity=1.0):
    # 4-point sparkle confined strictly to [cx-r, cx+r], [cy-r, cy+r]
    opacity_str = f' fill-opacity="{opacity:.2f}"' if opacity < 1.0 else ''
    return f'<path class="star" d="M {cx:.1f} {cy-r:.1f} Q {cx:.1f} {cy:.1f} {cx+r:.1f} {cy:.1f} Q {cx:.1f} {cy:.1f} {cx:.1f} {cy+r:.1f} Q {cx:.1f} {cy:.1f} {cx-r:.1f} {cy:.1f} Q {cx:.1f} {cy:.1f} {cx:.1f} {cy-r:.1f} Z" fill="{fill}"{opacity_str} />'

def generate_svg(calendar_data, filepath, width=1200, height=600):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except OSError as e:
        print(f"Filesystem error creating directory: {e}")
        return

    weeks = calendar_data.get("weeks", [])
    total_contributions = calendar_data.get("totalContributions", 0)
    
    # Calculate Statistics
    longest_streak = 0
    current_streak = 0
    month_counts = defaultdict(int)
    active_days = 0
    
    # Grid Layout Parameters
    cell_size = 14
    step = 18
    # Center grid horizontally
    grid_width = len(weeks) * step
    start_x = (width - grid_width) / 2
    start_y = 220
    
    grid_cells = []
    active_cells = []
    
    for col, week in enumerate(weeks):
        x = start_x + col * step
        for day in week.get("contributionDays", []):
            date_str = day["date"]
            count = day["contributionCount"]
            
            # Use real datetime to map row correctly (0=Mon, 6=Sun in Python)
            # Standard GitHub calendar aligns Sunday to row 0.
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            github_weekday = (dt.weekday() + 1) % 7
            y = start_y + github_weekday * step
            
            cell = {
                "x": x,
                "y": y,
                "date": date_str,
                "count": count
            }
            grid_cells.append(cell)
            
            # Stats updates
            if count > 0:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
                active_days += 1
                active_cells.append(cell)
            else:
                current_streak = 0
                
            month = date_str[0:7]
            month_counts[month] += count

    if not grid_cells:
        print("No days found in calendar.")
        return
        
    most_active_month = "N/A"
    if month_counts:
        best_month_str = max(month_counts.items(), key=lambda x: x[1])[0]
        try:
            dt = datetime.strptime(best_month_str, "%Y-%m")
            most_active_month = dt.strftime("%b %Y")
        except ValueError:
            most_active_month = best_month_str

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
    
    svg.append('    <rect x="193" y="-11" width="14" height="14" rx="3" fill="#161b22" />')
    
    svg.append('    <rect x="218" y="-11" width="14" height="14" rx="3" fill="#161b22" />')
    svg.append('    ' + draw_star(225, -4, 2.5, "#C084FC"))
    
    svg.append('    <rect x="243" y="-11" width="14" height="14" rx="3" fill="#161b22" />')
    svg.append('    ' + draw_star(250, -4, 3.5, "#C084FC"))
    
    svg.append('    <rect x="268" y="-11" width="14" height="14" rx="3" fill="#161b22" />')
    svg.append('    ' + draw_star(275, -4, 4.0, "#C084FC"))
    
    svg.append('    <rect x="293" y="-11" width="14" height="14" rx="3" fill="#161b22" />')
    svg.append('    ' + draw_star(300, -4, 4.5 * 1.4, "#A855F7", 0.4))
    svg.append('    ' + draw_star(300, -4, 4.5, "#C084FC"))
    svg.append('    ' + draw_star(300, -4, 2.0, "#F3E8FF"))
    
    svg.append('    <text x="320" y="0" fill="#8b949e" font-size="12">More</text>')
    svg.append('  </g>')

    # Month Labels (Top of grid)
    svg.append('  <g id="month-labels">')
    last_month = None
    for cell in grid_cells:
        month_str = cell["date"][5:7]
        if month_str != last_month:
            dt = datetime.strptime(cell["date"], "%Y-%m-%d")
            month_name = dt.strftime("%b")
            svg.append(f'    <text x="{cell["x"]:.1f}" y="{start_y - 15}" fill="#8b949e" font-size="12">{month_name}</text>')
            last_month = month_str
    svg.append('  </g>')

    # Grid - All Cells
    svg.append('  <g id="grid-cells">')
    for cell in grid_cells:
        svg.append(f'    <rect x="{cell["x"]:.1f}" y="{cell["y"]:.1f}" width="{cell_size}" height="{cell_size}" rx="3" fill="#161b22" />')
    svg.append('  </g>')

    # Grid - Active Cells & Stars
    svg.append('  <g id="active-cells">')
    
    for cell in active_cells:
        cx = cell["x"] + cell_size / 2
        cy = cell["y"] + cell_size / 2
        count = cell["count"]
        
        # Star size logic based on count (max radius 4.5 ensures it remains completely inside 14x14 cell)
        if count <= 2: r = 2.5
        elif count <= 5: r = 3.5
        elif count <= 10: r = 4.0
        else: r = 4.5
        
        # Glow (a larger, softer star shape, strictly bound inside the cell)
        glow_r = r * 1.4
        svg.append('    ' + draw_star(cx, cy, glow_r, "#A855F7", 0.4))
        
        # Star Main Shape
        svg.append('    ' + draw_star(cx, cy, r, "#C084FC"))
        
        # Brighter Center Core
        svg.append('    ' + draw_star(cx, cy, r * 0.45, "#F3E8FF"))

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
        svg.append(f'  <text x="{cx + card_width/2}" y="{stats_y + 60}" fill="#C084FC" font-size="22" font-weight="bold" text-anchor="middle">{value}</text>')

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
