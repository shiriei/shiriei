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

    # Prepare nodes
    active_nodes = []
    month_labels = []
    last_month = None
    
    total_days = len(all_days)
    for i, d in enumerate(all_days):
        x = 100 + (i / max(1, total_days - 1)) * 1000
        
        # Add month label
        month_str = d["date"][5:7]
        if month_str != last_month:
            try:
                dt = datetime.strptime(d["date"], "%Y-%m-%d")
                month_name = dt.strftime("%b")
                # Avoid overlapping labels at the very start
                if x > 120 or not month_labels:
                    month_labels.append({"x": x, "label": month_name})
            except ValueError:
                pass
            last_month = month_str
            
        if d["count"] > 0:
            # Deterministic wave layout ensuring organic chronological flow
            y = 280 + math.sin(i / 20.0) * 60 + math.cos(i / 7.0) * 30
            active_nodes.append({
                "index": i,
                "x": x,
                "y": y,
                "count": d["count"],
                "date": d["date"]
            })

    # Prepare edges
    edges = []
    for i in range(len(active_nodes)):
        idx_current = active_nodes[i]["index"]
        # Connect to the next active day chronologically
        if i + 1 < len(active_nodes):
            edges.append((i, i + 1))
            
        # Add one sparse secondary connection if it's very close in time to maintain visual continuity
        if i + 2 < len(active_nodes):
            idx_target = active_nodes[i+2]["index"]
            if (idx_target - idx_current) <= 7:
                edges.append((i, i + 2))

    # Build SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '  <style>',
        '    .node { transition: all 0.3s ease; }',
        '    .node:hover { stroke: #ffffff; stroke-width: 2px; }',
        '    text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }',
        '  </style>',
        f'  <rect width="{width}" height="{height}" fill="#0d1117" rx="15" />'
    ]
    
    # Title
    svg.append('  <text x="100" y="60" fill="#c9d1d9" font-size="28" font-weight="bold">Contribution Network</text>')
    svg.append('  <text x="100" y="90" fill="#8b949e" font-size="16">GitHub activity &bull; Last 12 months</text>')
    
    # Legend
    svg.append('  <g transform="translate(800, 70)">')
    svg.append('    <text x="0" y="0" fill="#8b949e" font-size="14">Contribution intensity</text>')
    svg.append('    <text x="160" y="0" fill="#8b949e" font-size="12">Less</text>')
    svg.append('    <circle cx="200" cy="-4" r="3" fill="#FF9BCE" fill-opacity="0.3"/>')
    svg.append('    <circle cx="220" cy="-4" r="4.5" fill="#FF9BCE" fill-opacity="0.5"/>')
    svg.append('    <circle cx="240" cy="-4" r="6" fill="#FF9BCE" fill-opacity="0.7"/>')
    svg.append('    <circle cx="260" cy="-4" r="7.5" fill="#FF9BCE" fill-opacity="0.9"/>')
    svg.append('    <circle cx="280" cy="-4" r="9" fill="#FF9BCE" fill-opacity="1.0"/>')
    svg.append('    <text x="300" y="0" fill="#8b949e" font-size="12">More</text>')
    svg.append('  </g>')
    
    # Month Labels
    for m in month_labels:
        svg.append(f'  <text x="{m["x"]:.1f}" y="150" fill="#8b949e" font-size="12" text-anchor="middle">{m["label"]}</text>')

    # Network Edges
    svg.append('  <g>')
    for u_idx, v_idx in edges:
        u = active_nodes[u_idx]
        v = active_nodes[v_idx]
        svg.append(f'    <line x1="{u["x"]:.1f}" y1="{u["y"]:.1f}" x2="{v["x"]:.1f}" y2="{v["y"]:.1f}" stroke="#FF9BCE" stroke-width="1" stroke-opacity="0.2" />')

    # Network Nodes
    for n in active_nodes:
        r = min(12.0, 3.0 + math.log1p(n["count"]) * 2.0)
        opacity = min(1.0, 0.3 + math.log1p(n["count"]) * 0.2)
        svg.append(f'    <circle class="node" cx="{n["x"]:.1f}" cy="{n["y"]:.1f}" r="{r:.1f}" fill="#FF9BCE" fill-opacity="{opacity:.2f}">')
        svg.append(f'      <title>Date: {n["date"]}&#10;Contributions: {n["count"]}</title>')
        svg.append('    </circle>')
    svg.append('  </g>')

    # Summary Statistics
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
        svg.append(f'  <text x="{cx + card_width/2}" y="{stats_y + 60}" fill="#FF9BCE" font-size="22" font-weight="bold" text-anchor="middle">{value}</text>')

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
