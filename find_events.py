import urllib.request
import urllib.parse
import json
import math
import sys
import os
from datetime import datetime

def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            encoding = sys.stdout.encoding or 'utf-8'
            print(text.encode(encoding, errors='replace').decode(encoding))
        except Exception:
            try:
                print(text.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            except Exception:
                pass

# Default parameters
DEFAULT_LAT = 27.9506
DEFAULT_LON = -82.4572
DEFAULT_RADIUS = 100

def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 9999.0
    R = 3958.8  # Earth radius in miles
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading config.json: {e}", file=sys.stderr)
    return {}

def detect_location_from_ip():
    url = "http://ip-api.com/json"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        print("Detecting location dynamically from public IP...")
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('status') == 'success':
                loc = {
                    'lat': float(data.get('lat', DEFAULT_LAT)),
                    'lon': float(data.get('lon', DEFAULT_LON)),
                    'city': data.get('city', "Detected Location"),
                    'region': data.get('regionName', "")
                }
                print(f"Detected Location: {loc['city']}, {loc['region']} ({loc['lat']}, {loc['lon']})")
                return loc
    except Exception as e:
        print(f"IP Geolocation failed: {e}. Using defaults.", file=sys.stderr)
    return {
        'lat': DEFAULT_LAT,
        'lon': DEFAULT_LON,
        'city': "Tampa",
        'region': "Florida"
    }

def get_events(game_slug, lat=None, lon=None, radius=None, keyword=None):
    events = []
    page = 1
    
    if lat is not None and lon is not None and radius is not None:
        url = f"https://api.riftbound.uvsgames.com/api/v2/events/?latitude={lat}&longitude={lon}&num_miles={radius}&game_slug={game_slug}&upcoming_only=true&page_size=100"
    else:
        url = f"https://api.riftbound.uvsgames.com/api/v2/events/?game_slug={game_slug}&upcoming_only=true&page_size=100"
        if keyword:
            url += f"&name={urllib.parse.quote(keyword)}"
            
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    print(f"Fetching {game_slug} events (URL: {url})...")
    max_pages = 15 if game_slug == "disney-lorcana" else 40
    
    while url and page <= max_pages:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                results = data.get('results', [])
                events.extend(results)
                url = data.get('next')
                page += 1
        except Exception as e:
            print(f"Error fetching page {page} for {game_slug}: {e}", file=sys.stderr)
            break
            
    print(f"Retrieved {len(events)} total upcoming events for {game_slug}.")
    return events

def filter_and_format_events(events, game_type, keywords, user_lat=None, user_lon=None):
    filtered = []
    for item in events:
        name = item.get('name', '')
        desc = item.get('description', '') or ''
        
        # Check keywords
        matches_keyword = False
        for kw in keywords:
            if kw.lower() in name.lower() or kw.lower() in desc.lower():
                matches_keyword = True
                break
                
        if not matches_keyword:
            continue
            
        store = item.get('store', {}) or {}
        store_name = store.get('name', 'Unknown Store')
        store_address = store.get('full_address', item.get('full_address', 'Unknown Address'))
        store_website = store.get('website')
        store_email = store.get('email')
        
        # Extract store coordinates
        store_lat = store.get('latitude') or item.get('latitude')
        store_lon = store.get('longitude') or item.get('longitude')
        try:
            event_lat = float(store_lat) if store_lat is not None else None
            event_lon = float(store_lon) if store_lon is not None else None
        except (ValueError, TypeError):
            event_lat = None
            event_lon = None
        
        start_str = item.get('start_datetime', '')
        # Parse start date
        date_formatted = "Unknown Date"
        time_formatted = "Unknown Time"
        sort_dt = datetime.max
        if start_str:
            try:
                clean_str = start_str
                if clean_str.endswith('Z'):
                    clean_str = clean_str[:-1] + '+00:00'
                dt = datetime.fromisoformat(clean_str)
                sort_dt = dt
                date_formatted = dt.strftime("%A, %B %d, %Y")
                time_formatted = dt.strftime("%I:%M %p %Z").strip()
            except Exception as ex:
                pass
                
        event_id = item.get('id')
        if game_type == 'Lorcana':
            reg_url = f"https://tcg.ravensburgerplay.com/events/{event_id}"
        else:
            reg_url = f"https://locator.riftbound.uvsgames.com/events/{event_id}"
            
        cost_cents = item.get('cost_in_cents', 0)
        cost_str = "Free" if cost_cents == 0 else f"${cost_cents / 100:.2f}"
        
        capacity = item.get('capacity')
        reg_count = item.get('registered_user_count', 0)
        spots_str = f"{reg_count} registered"
        if capacity:
            spots_str += f" / {capacity} max"
            
        # Calculate distance if user coords are available, otherwise use API distance or 9999.0
        if user_lat is not None and user_lon is not None and event_lat is not None and event_lon is not None:
            dist = haversine(user_lat, user_lon, event_lat, event_lon)
        else:
            dist = item.get('distance_in_miles') or 9999.0
        
        filtered.append({
            'id': event_id,
            'name': name,
            'description': desc,
            'game_type': game_type,
            'date': date_formatted,
            'time': time_formatted,
            'sort_dt_iso': sort_dt.isoformat() if sort_dt != datetime.max else "",
            'store_name': store_name,
            'store_address': store_address,
            'store_website': store_website,
            'store_email': store_email,
            'cost': cost_str,
            'cost_cents': cost_cents,
            'spots': spots_str,
            'distance': dist,
            'lat': event_lat,
            'lon': event_lon,
            'url': reg_url
        })
        
    return filtered

def generate_html_report(events, lat, lon, radius, location_name, output_file):
    now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")
    
    # Sort events by date initially
    events.sort(key=lambda x: x['sort_dt_iso'])
    
    # JSON dump for embedding
    events_json = json.dumps(events, indent=2)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playhub Weekly Event Matcher</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="style.css">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --accent-lorcana: #eab308;
            --accent-riftbound: #3b82f6;
            --gradient-lorcana: linear-gradient(135deg, #f59e0b, #d97706);
            --gradient-riftbound: linear-gradient(135deg, #3b82f6, #1d4ed8);
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            background: radial-gradient(circle at top right, #111827, #070a13);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            color: var(--text-color);
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        h1 {{
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: -0.05em;
            margin: 0 0 10px 0;
            background: linear-gradient(to right, #ffffff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .meta-info {{
            font-size: 1rem;
            color: var(--text-muted);
            margin-top: 10px;
            font-family: 'Inter', sans-serif;
            line-height: 1.5;
        }}
        
        .meta-info strong {{
            color: #ffffff;
        }}
        
        /* Interactive Control Panel Styling */
        .control-panel {{
            background: rgba(17, 24, 39, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 24px;
            margin-bottom: 40px;
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .filter-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 24px;
            align-items: center;
        }}
        
        .filter-group {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            flex: 1;
            min-width: 200px;
        }}
        
        .filter-group label {{
            font-size: 0.9rem;
            font-weight: 600;
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        .search-input-wrapper {{
            position: relative;
        }}
        
        .search-input-wrapper input {{
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
            color: #ffffff;
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }}
        
        .search-input-wrapper input:focus {{
            border-color: var(--accent-riftbound);
        }}
        
        .slider-wrapper {{
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        
        .slider-wrapper input[type="range"] {{
            flex: 1;
            accent-color: var(--accent-riftbound);
            cursor: pointer;
        }}
        
        .slider-value {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
            min-width: 70px;
            text-align: right;
        }}
        
        .toggle-group {{
            display: flex;
            gap: 12px;
        }}
        
        .toggle-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 18px;
            color: var(--text-muted);
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .toggle-btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }}
        
        .toggle-btn.active.lorcana-toggle {{
            background: rgba(234, 179, 8, 0.15);
            color: var(--accent-lorcana);
            border-color: var(--accent-lorcana);
        }}
        
        .toggle-btn.active.riftbound-toggle {{
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-riftbound);
            border-color: var(--accent-riftbound);
        }}
        
        .config-help {{
            font-size: 0.85rem;
            color: var(--text-muted);
            font-family: 'Inter', sans-serif;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 14px;
        }}
        
        /* Grid Layout */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
        }}
        
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .section-title {{
            font-size: 1.8rem;
            font-weight: 600;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            letter-spacing: -0.02em;
        }}
        
        .section-title.lorcana {{
            color: var(--accent-lorcana);
        }}
        
        .section-title.riftbound {{
            color: var(--accent-riftbound);
        }}
        
        .badge {{
            font-size: 0.8rem;
            padding: 4px 10px;
            border-radius: 9999px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }}
        
        .badge.lorcana-bg {{
            background: rgba(234, 179, 8, 0.15);
            color: var(--accent-lorcana);
            border: 1px solid rgba(234, 179, 8, 0.2);
        }}
        
        .badge.riftbound-bg {{
            background: rgba(59, 130, 246, 0.15);
            color: var(--accent-riftbound);
            border: 1px solid rgba(59, 130, 246, 0.2);
        }}
        
        .card-list {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .no-events {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            color: var(--text-muted);
            font-family: 'Inter', sans-serif;
        }}
        
        .event-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        
        .event-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
        }}
        
        .event-card.lorcana-card::before {{
            background: var(--gradient-lorcana);
        }}
        
        .event-card.riftbound-card::before {{
            background: var(--gradient-riftbound);
        }}
        
        .event-card:hover {{
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 20px -10px rgba(0, 0, 0, 0.5);
            background: rgba(30, 41, 59, 0.7);
        }}
        
        .event-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
            gap: 16px;
        }}
        
        .event-name {{
            font-size: 1.3rem;
            font-weight: 600;
            margin: 0;
            color: #ffffff;
            line-height: 1.3;
        }}
        
        .event-distance {{
            font-size: 0.9rem;
            font-weight: 600;
            color: #ffffff;
            background: rgba(255, 255, 255, 0.08);
            padding: 4px 8px;
            border-radius: 6px;
            white-space: nowrap;
        }}
        
        .event-details {{
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-bottom: 18px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .detail-row {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .detail-row svg {{
            width: 16px;
            height: 16px;
            flex-shrink: 0;
        }}
        
        .event-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: auto;
            padding-top: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.04);
        }}
        
        .event-cost {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #ffffff;
        }}
        
        .btn-register {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: 'Inter', sans-serif;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            color: #ffffff;
            padding: 8px 16px;
            border-radius: 8px;
            transition: opacity 0.2s;
        }}
        
        .lorcana-card .btn-register {{
            background: var(--gradient-lorcana);
        }}
        
        .riftbound-card .btn-register {{
            background: var(--gradient-riftbound);
        }}
        
        .btn-register:hover {{
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Playhub Weekly Match Finder</h1>
            <div class="meta-info">
                Report generated on <strong>{now_str}</strong><br>
                Current Search Center: <strong id="center-display-name">{location_name}</strong> (<span id="center-lat">{lat}</span>, <span id="center-lon">{lon}</span>)
            </div>
        </header>
        
        <!-- Interactive client-side control panel -->
        <div class="control-panel">
            <div class="filter-row">
                <!-- Real-time text search -->
                <div class="filter-group" style="flex: 2; min-width: 250px;">
                    <label for="search-input">Search Events</label>
                    <div class="search-input-wrapper">
                        <input type="text" id="search-input" placeholder="Search by name, store, or address...">
                    </div>
                </div>
                
                <!-- Client-side location search -->
                <div class="filter-group" style="flex: 2; min-width: 250px;">
                    <label for="location-input">Search Center Location</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="location-input" placeholder="City, State, Zip or Country..." style="flex: 1; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 16px; color: #ffffff; font-family: 'Inter', sans-serif; font-size: 0.95rem; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='var(--accent-riftbound)'" onblur="this.style.borderColor='var(--border-color)'">
                        <button id="location-search-btn" style="background: var(--gradient-riftbound); border: none; border-radius: 10px; color: #ffffff; padding: 0 20px; font-family: 'Inter', sans-serif; font-weight: 600; cursor: pointer; transition: opacity 0.2s;" onmouseover="this.style.opacity=0.9" onmouseout="this.style.opacity=1">Search</button>
                    </div>
                    <div id="location-status" style="font-size: 0.8rem; color: var(--text-muted); margin-top: 4px; font-family: 'Inter', sans-serif;"></div>
                </div>
            </div>
            
            <div class="filter-row" style="margin-top: 10px;">
                <!-- Client-side distance slider -->
                <div class="filter-group" style="flex: 1; min-width: 200px;">
                    <label for="distance-slider">Distance Radius (max <span id="max-distance-label">500</span> mi)</label>
                    <div class="slider-wrapper">
                        <input type="range" id="distance-slider" min="1" max="500" value="{radius}">
                        <div class="slider-value" id="distance-display">{radius} mi</div>
                    </div>
                </div>

                <!-- Client-side date filter -->
                <div class="filter-group" style="flex: 1; min-width: 200px;">
                    <label for="date-filter">Date Range</label>
                    <select id="date-filter" style="width: 100%; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--border-color); border-radius: 10px; padding: 12px 16px; color: #ffffff; font-family: 'Inter', sans-serif; font-size: 0.95rem; outline: none; transition: border-color 0.2s;" onfocus="this.style.borderColor='var(--accent-riftbound)'" onblur="this.style.borderColor='var(--border-color)'">
                        <option value="all">All Upcoming Dates</option>
                        <option value="7">Next 7 Days</option>
                        <option value="14">Next 14 Days</option>
                        <option value="30">Next 30 Days</option>
                        <option value="60">Next 60 Days</option>
                    </select>
                </div>
                
                <!-- Toggles for games -->
                <div class="filter-group" style="flex: 0 0 auto;">
                    <label>Toggle Games</label>
                    <div class="toggle-group">
                        <button id="toggle-lorcana" class="toggle-btn active lorcana-toggle">Lorcana</button>
                        <button id="toggle-riftbound" class="toggle-btn active riftbound-toggle">Riftbound</button>
                    </div>
                </div>
            </div>
            
            <div class="config-help">
                💡 To query a new search center, change your radius limit, or adjust keywords, edit the <code style="color: #60a5fa; background: rgba(96, 165, 250, 0.1); padding: 2px 6px; border-radius: 4px;">config.json</code> file in your project folder and run <code style="color: #34d399; background: rgba(52, 211, 153, 0.1); padding: 2px 6px; border-radius: 4px;">run_weekly.bat</code>.
            </div>
        </div>
        
        <div class="dashboard-grid">
            <!-- LORCANA SECTION -->
            <div id="lorcana-section">
                <div class="section-title lorcana">
                    <span>Disney Lorcana Championships</span>
                    <span class="badge lorcana-bg" id="lorcana-count">0 Found</span>
                </div>
                <div class="card-list" id="lorcana-container">
                    <!-- Cards will be populated dynamically -->
                </div>
            </div>
            
            <!-- RIFTBOUND SECTION -->
            <div id="riftbound-section">
                <div class="section-title riftbound">
                    <span>Riftbound Skirmishes</span>
                    <span class="badge riftbound-bg" id="riftbound-count">0 Found</span>
                </div>
                <div class="card-list" id="riftbound-container">
                    <!-- Cards will be populated dynamically -->
                </div>
            </div>
        </div>
    </div>

    <!-- Embedded pre-baked JSON data -->
    <script>
        const ALL_EVENTS = {events_json};
        
        let showLorcana = true;
        let showRiftbound = true;
        let maxDistance = {radius};
        let searchQuery = "";
        let currentLat = {lat};
        let currentLon = {lon};
        let maxDays = "all";
        
        const searchInput = document.getElementById("search-input");
        const distanceSlider = document.getElementById("distance-slider");
        const distanceDisplay = document.getElementById("distance-display");
        const dateFilter = document.getElementById("date-filter");
        const toggleLorcanaBtn = document.getElementById("toggle-lorcana");
        const toggleRiftboundBtn = document.getElementById("toggle-riftbound");
        
        const locationInput = document.getElementById("location-input");
        const locationSearchBtn = document.getElementById("location-search-btn");
        const locationStatus = document.getElementById("location-status");
        const centerDisplayName = document.getElementById("center-display-name");
        const centerLatSpan = document.getElementById("center-lat");
        const centerLonSpan = document.getElementById("center-lon");
        
        const lorcanaContainer = document.getElementById("lorcana-container");
        const riftboundContainer = document.getElementById("riftbound-container");
        const lorcanaCount = document.getElementById("lorcana-count");
        const riftboundCount = document.getElementById("riftbound-count");
        
        const lorcanaSection = document.getElementById("lorcana-section");
        const riftboundSection = document.getElementById("riftbound-section");
        
        // Haversine formula client-side
        function calculateHaversine(lat1, lon1, lat2, lon2) {{
            if (lat1 === null || lon1 === null || lat2 === null || lon2 === null) return 9999;
            const R = 3958.8; // miles
            const dLat = (lat2 - lat1) * Math.PI / 180;
            const dLon = (lon2 - lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                      Math.sin(dLon/2) * Math.sin(dLon/2);
            const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            return R * c;
        }}
        
        // Geocode address using Nominatim
        async function geocodeAddress(address) {{
            if (!address.trim()) return;
            locationStatus.textContent = "🔍 Geocoding location...";
            locationStatus.style.color = "var(--text-muted)";
            try {{
                const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${{encodeURIComponent(address)}}&limit=1`, {{
                    headers: {{
                        'Accept': 'application/json'
                    }}
                }});
                const data = await response.json();
                if (data && data.length > 0) {{
                    const lat = parseFloat(data[0].lat);
                    const lon = parseFloat(data[0].lon);
                    const name = data[0].display_name.split(',')[0] + ', ' + (data[0].display_name.split(',')[1] || '').trim();
                    
                    currentLat = lat;
                    currentLon = lon;
                    
                    centerDisplayName.textContent = name;
                    centerLatSpan.textContent = lat.toFixed(4);
                    centerLonSpan.textContent = lon.toFixed(4);
                    locationStatus.textContent = "✅ Location updated successfully!";
                    locationStatus.style.color = "#34d399";
                    
                    // Recalculate distances for all events
                    ALL_EVENTS.forEach(ev => {{
                        ev.distance = calculateHaversine(currentLat, currentLon, ev.lat, ev.lon);
                    }});
                    
                    renderEvents();
                }} else {{
                    locationStatus.textContent = "❌ Location not found. Try adding city/state.";
                    locationStatus.style.color = "#f87171";
                }}
            }} catch (error) {{
                console.error("Geocoding error:", error);
                locationStatus.textContent = "❌ Error connecting to geocoder.";
                locationStatus.style.color = "#f87171";
            }}
        }}
        
        // Render events client-side based on active filters
        function renderEvents() {{
            // Filter elements
            const now = new Date();
            const filtered = ALL_EVENTS.filter(ev => {{
                // Game toggle
                if (ev.game_type === "Lorcana" && !showLorcana) return false;
                if (ev.game_type === "Riftbound" && !showRiftbound) return false;
                
                // Distance check
                if (ev.distance > maxDistance) return false;
                
                // Date range check
                if (maxDays !== "all" && ev.sort_dt_iso) {{
                    const eventDate = new Date(ev.sort_dt_iso);
                    const diffTime = eventDate - now;
                    const diffDays = diffTime / (1000 * 60 * 60 * 24);
                    if (diffDays > parseInt(maxDays)) return false;
                }}
                
                // Search query check
                if (searchQuery) {{
                    const q = searchQuery.toLowerCase();
                    const nameMatch = ev.name.toLowerCase().includes(q);
                    const storeMatch = ev.store_name.toLowerCase().includes(q);
                    const addressMatch = ev.store_address.toLowerCase().includes(q);
                    const descMatch = (ev.description || "").toLowerCase().includes(q);
                    if (!nameMatch && !storeMatch && !addressMatch && !descMatch) return false;
                }}
                
                return true;
            }});
            
            // Separate lists and sort by distance
            const lorcanaList = filtered.filter(ev => ev.game_type === "Lorcana").sort((a, b) => a.distance - b.distance);
            const riftboundList = filtered.filter(ev => ev.game_type === "Riftbound").sort((a, b) => a.distance - b.distance);
            
            // Show/Hide section column if game toggle is unchecked
            lorcanaSection.style.display = showLorcana ? "block" : "none";
            riftboundSection.style.display = showRiftbound ? "block" : "none";
            
            // Update badges
            lorcanaCount.textContent = `${{lorcanaList.length}} Found`;
            riftboundCount.textContent = `${{riftboundList.length}} Found`;
            
            // Render Lorcana
            lorcanaContainer.innerHTML = lorcanaList.length === 0 
                ? `<div class="no-events">No matching Lorcana events within range.</div>`
                : lorcanaList.map(ev => generateEventCard(ev, "lorcana")).join("");
                
            // Render Riftbound
            riftboundContainer.innerHTML = riftboundList.length === 0 
                ? `<div class="no-events">No matching Riftbound skirmishes within range.</div>`
                : riftboundList.map(ev => generateEventCard(ev, "riftbound")).join("");
        }}
        
        function generateEventCard(ev, styleClass) {{
            const distStr = ev.distance !== 9999 ? `${{ev.distance.toFixed(1)}} mi` : "Unknown dist";
            return `
                <div class="event-card ${{styleClass}}-card">
                    <div>
                        <div class="event-header">
                            <h3 class="event-name">${{ev.name}}</h3>
                            <span class="event-distance">${{distStr}}</span>
                        </div>
                        <div class="event-details">
                            <div class="detail-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                                <span>${{ev.date}}</span>
                            </div>
                            <div class="detail-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                                <span>${{ev.time}}</span>
                            </div>
                            <div class="detail-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
                                <span>${{ev.store_name}} (${{ev.store_address}})</span>
                            </div>
                            <div class="detail-row">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
                                <span>${{ev.spots}}</span>
                            </div>
                        </div>
                    </div>
                    <div class="event-footer">
                        <span class="event-cost">${{ev.cost}}</span>
                        <a href="${{ev.url}}" target="_blank" class="btn-register">
                            View Details
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
                        </a>
                    </div>
                </div>
            `;
        }}
        
        // Listeners
        searchInput.addEventListener("input", (e) => {{
            searchQuery = e.target.value;
            renderEvents();
        }});
        
        distanceSlider.addEventListener("input", (e) => {{
            maxDistance = Number(e.target.value);
            distanceDisplay.textContent = `${{maxDistance}} mi`;
            renderEvents();
        }});
        
        dateFilter.addEventListener("change", (e) => {{
            maxDays = e.target.value;
            renderEvents();
        }});
        
        toggleLorcanaBtn.addEventListener("click", () => {{
            showLorcana = !showLorcana;
            toggleLorcanaBtn.classList.toggle("active", showLorcana);
            renderEvents();
        }});
        
        toggleRiftboundBtn.addEventListener("click", () => {{
            showRiftbound = !showRiftbound;
            toggleRiftboundBtn.classList.toggle("active", showRiftbound);
            renderEvents();
        }});
        
        locationInput.addEventListener("keypress", (e) => {{
            if (e.key === "Enter") {{
                geocodeAddress(locationInput.value);
            }}
        }});
        
        locationSearchBtn.addEventListener("click", () => {{
            geocodeAddress(locationInput.value);
        }});
        
        // Initial load (calculate distances from the default location first)
        ALL_EVENTS.forEach(ev => {{
            ev.distance = calculateHaversine(currentLat, currentLon, ev.lat, ev.lon);
        }});
        renderEvents();
    </script>
</body>
</html>
"""
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML report successfully generated at: {output_file}")

def main():
    # Load configuration
    config = load_config()
    
    auto_detect = config.get("auto_detect_location", True)
    default_lat = config.get("default_latitude", DEFAULT_LAT)
    default_lon = config.get("default_longitude", DEFAULT_LON)
    radius = config.get("radius_miles", DEFAULT_RADIUS)
    global_mode = config.get("global_mode", False) or "GITHUB_ACTIONS" in os.environ
    
    lorcana_keywords = config.get("lorcana_keywords", ["championship", "championset", "champion"])
    riftbound_keywords = config.get("riftbound_keywords", ["skirmish"])
    
    # 1. Geolocation detection
    if global_mode:
        print("Running in Global Mode (fetching upcoming events globally and filtering by key terms)...")
        lat = default_lat
        lon = default_lon
        location_name = "Tampa, FL"
    else:
        # Skip dynamic IP location detection under GitHub Actions to avoid geolocating the runner's server center.
        if auto_detect and "GITHUB_ACTIONS" not in os.environ:
            loc = detect_location_from_ip()
            lat = loc['lat']
            lon = loc['lon']
            location_name = f"{loc['city']}, {loc['region']}"
        else:
            lat = default_lat
            lon = default_lon
            location_name = "Configured Location"
            
    # Optional arguments parser overrides
    if len(sys.argv) >= 3:
        try:
            lat = float(sys.argv[1])
            lon = float(sys.argv[2])
            location_name = "Command Line Arguments"
            if len(sys.argv) >= 4:
                radius = int(sys.argv[3])
            global_mode = False # Manual coordinates override global mode
        except:
            print("Invalid arguments. Usage: python find_events.py [latitude] [longitude] [radius_miles]")
            sys.exit(1)
            
    if global_mode:
        print(f"Searching events globally. Initial center set to: {location_name} ({lat}, {lon})")
        lorcana_raw = get_events("disney-lorcana", keyword="champion")
        riftbound_raw = get_events("riftbound", keyword="skirmish")
    else:
        print(f"Searching events within {radius} miles of coordinates ({lat}, {lon}) ({location_name})")
        lorcana_raw = get_events("disney-lorcana", lat, lon, radius)
        riftbound_raw = get_events("riftbound", lat, lon, radius)
        
    lorcana_matches = filter_and_format_events(lorcana_raw, "Lorcana", lorcana_keywords, user_lat=lat, user_lon=lon)
    riftbound_matches = filter_and_format_events(riftbound_raw, "Riftbound", riftbound_keywords, user_lat=lat, user_lon=lon)
    
    all_matches = lorcana_matches + riftbound_matches
    
    safe_print("\n" + "="*50)
    safe_print(f"FOUND {len(lorcana_matches)} LORCANA CHAMPIONSHIPS:")
    safe_print("="*50)
    for idx, ev in enumerate(lorcana_matches, 1):
        dist_str = f"{ev['distance']:.1f} miles away" if ev['distance'] != 9999.0 else "distance unknown"
        safe_print(f"{idx}. {ev['name']}")
        safe_print(f"   Date: {ev['date']} at {ev['time']}")
        safe_print(f"   Store: {ev['store_name']} ({dist_str})")
        safe_print(f"   Spots: {ev['spots']} | Cost: {ev['cost']}")
        safe_print("-" * 50)
        
    safe_print("\n" + "="*50)
    safe_print(f"FOUND {len(riftbound_matches)} RIFTBOUND SKIRMISHES:")
    safe_print("="*50)
    for idx, ev in enumerate(riftbound_matches, 1):
        dist_str = f"{ev['distance']:.1f} miles away" if ev['distance'] != 9999.0 else "distance unknown"
        safe_print(f"{idx}. {ev['name']}")
        safe_print(f"   Date: {ev['date']} at {ev['time']}")
        safe_print(f"   Store: {ev['store_name']} ({dist_str})")
        safe_print(f"   Spots: {ev['spots']} | Cost: {ev['cost']}")
        safe_print("-" * 50)
        
    # Generate HTML report in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_html = os.path.join(script_dir, "index.html")
    generate_html_report(all_matches, lat, lon, radius, location_name, output_html)

if __name__ == "__main__":
    main()
