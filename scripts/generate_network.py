import os
import json
import urllib.request
import urllib.error
import math
import random
from datetime import datetime

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
                return []
                
            user_data = result.get("data", {}).get("user")
            if not user_data:
                print("User not found or no data returned.")
                return []
                
            weeks = user_data["contributionsCollection"]["contributionCalendar"]["weeks"]
            days = []
            for week in weeks:
                for day in week["contributionDays"]:
                    if day["contributionCount"] > 0:
                        days.append(day)
            return days
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
        return []
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}")
        return []

class Node:
    def __init__(self, id, date, count):
        self.id = id
        self.date = date
        self.count = count
        self.x = 0
        self.y = 0
        self.dx = 0
        self.dy = 0

def generate_layout(days, width=800, height=400):
    nodes = [Node(i, d["date"], d["contributionCount"]) for i, d in enumerate(days)]
    if not nodes:
        return [], []
        
    # Initial spiral placement for an organic starting shape
    for i, n in enumerate(nodes):
        angle = i * 0.8
        radius = 10 + i * 1.5
        n.x = width / 2 + math.cos(angle) * radius
        n.y = height / 2 + math.sin(angle) * radius

    edges = []
    # Create connections for the network
    for i in range(len(nodes)):
        if i + 1 < len(nodes):
            edges.append((i, i + 1))
        # Add pseudo-random cross links for organic look
        if i + 7 < len(nodes):
            edges.append((i, i + 7))
        elif i + 4 < len(nodes):
            edges.append((i, i + 4))

    # Force-directed layout
    k = math.sqrt(width * height / len(nodes))
    temperature = width / 10.0

    for iteration in range(75):
        for n in nodes:
            n.dx = 0
            n.dy = 0
            
        # Repulsion
        for i, u in enumerate(nodes):
            for j, v in enumerate(nodes[i+1:], i+1):
                dx = u.x - v.x
                dy = u.y - v.y
                dist = math.hypot(dx, dy)
                if dist == 0:
                    dx = random.uniform(-0.1, 0.1)
                    dy = random.uniform(-0.1, 0.1)
                    dist = math.hypot(dx, dy)
                if dist < 150:
                    force = (k * k) / dist
                    u.dx += (dx / dist) * force
                    v.dx -= (dx / dist) * force
                    
        # Attraction
        for u_idx, v_idx in edges:
            u = nodes[u_idx]
            v = nodes[v_idx]
            dx = v.x - u.x
            dy = v.y - u.y
            dist = math.hypot(dx, dy)
            if dist == 0:
                dx = random.uniform(-0.1, 0.1)
                dy = random.uniform(-0.1, 0.1)
                dist = math.hypot(dx, dy)
            force = (dist * dist) / k
            u.dx += (dx / dist) * force
            v.dx -= (dx / dist) * force
                
        # Update positions
        for n in nodes:
            disp = math.hypot(n.dx, n.dy)
            if disp > 0:
                n.x += (n.dx / disp) * min(disp, temperature)
                n.y += (n.dy / disp) * min(disp, temperature)
                
        temperature *= 0.95

    # Normalize to canvas
    min_x = min(n.x for n in nodes)
    max_x = max(n.x for n in nodes)
    min_y = min(n.y for n in nodes)
    max_y = max(n.y for n in nodes)
    
    if max_x == min_x: max_x = min_x + 1
    if max_y == min_y: max_y = min_y + 1
    
    pad = 40
    for n in nodes:
        n.x = pad + (n.x - min_x) / (max_x - min_x) * (width - 2 * pad)
        n.y = pad + (n.y - min_y) / (max_y - min_y) * (height - 2 * pad)
        
    return nodes, edges

def generate_svg(nodes, edges, filepath, width=800, height=400):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except OSError as e:
        print(f"Filesystem error creating directory: {e}")
        return
        
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '  <style>',
        '    .node { transition: all 0.3s ease; }',
        '    .node:hover { stroke: #ffffff; stroke-width: 2px; }',
        '  </style>',
        '  <g>'
    ]
    
    # Draw edges
    for u_idx, v_idx in edges:
        u = nodes[u_idx]
        v = nodes[v_idx]
        svg.append(
            f'    <line x1="{u.x:.2f}" y1="{u.y:.2f}" x2="{v.x:.2f}" y2="{v.y:.2f}" '
            f'stroke="#58A6FF" stroke-width="1" stroke-opacity="0.25" />'
        )
        
    # Draw nodes
    for n in nodes:
        r = 2 + math.log1p(n.count) * 1.5
        opacity = min(0.9, 0.4 + (n.count * 0.05))
        svg.append(
            f'    <circle class="node" cx="{n.x:.2f}" cy="{n.y:.2f}" r="{r:.2f}" '
            f'fill="#58A6FF" fill-opacity="{opacity:.2f}">'
        )
        svg.append(f'      <title>Date: {n.date}&#10;Contributions: {n.count}</title>')
        svg.append('    </circle>')
        
    svg.append('  </g>')
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
    days = fetch_contributions(username, token)
    
    if not days:
        print("No contribution data found or error occurred.")
        return
        
    print(f"Generating network for {len(days)} active days...")
    nodes, edges = generate_layout(days)
    
    output_file = os.path.join("output", "contribution-network.svg")
    generate_svg(nodes, edges, output_file)
    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    main()
