# Playhub Weekly Match Finder

A zero-dependency, automated competitive card game event finder. It fetches, filters, and generates a visual dashboard of upcoming **Disney Lorcana Store Championships** and **Riftbound Summoner Skirmishes** within a specified radius of your location.

## Theme Version
Theme Version: 1.0.9

---

## Features
*   **Zero Dependencies:** Built entirely using Python's standard libraries—no `pip install` required.
*   **Dual Game Support:** Pulls Lorcana and Riftbound events directly from active Playhub endpoints.
*   **Automatic IP Geolocation:** Detects your public IP coordinates dynamically at runtime to calculate proximity (with manual overrides).
*   **Rich HTML Web Dashboard:** Compiles matches into a dark-mode, mobile-friendly interactive dashboard (`events_report.html`) complete with:
    *   Real-time search filtering.
    *   Distance radius slider.
    *   Game section show/hide toggles.
    *   Registration links, fees, and seating capacity info.
*   **Background Automation:** Includes built-in scheduling helpers to update the reports weekly.

## Project Structure
*   `find_events.py` - Core search and formatting logic.
*   `style.css` - UI Styling for the generated report.
*   `config.example.json` - Configuration template.
*   `run_weekly.bat` - Windows batch execution script.
*   `schedule_task.ps1` - Windows Task Scheduler automated setup script.

## Setup Instructions

### 1. Pre-requisites
*   Make sure you have [Python 3.x](https://www.python.org/) installed.

### 2. Installation
Clone the repository:
```bash
git clone https://github.com/yourusername/playhub-event-finder.git
cd playhub-event-finder
```

### 3. Configuration
Copy the template configuration file:
*   **Windows (Command Prompt):**
    ```cmd
    copy config.example.json config.json
    ```
*   **macOS / Linux:**
    ```bash
    cp config.example.json config.json
    ```

Open `config.json` in your favorite text editor to configure settings:
```json
{
    "auto_detect_location": true,
    "default_latitude": 27.9506,
    "default_longitude": -82.4572,
    "radius_miles": 100,
    "global_mode": false,
    "lorcana_keywords": ["championship", "championset", "champion"],
    "riftbound_keywords": ["skirmish"]
}
```
*   `auto_detect_location`: If `true`, the script queries `http://ip-api.com` on startup to detect your IP's current coordinates.
*   `default_latitude` / `default_longitude`: Used as fallbacks if IP detection fails, or as manual overrides if `auto_detect_location` is `false`. Defaults to Tampa, FL.
*   `radius_miles`: Search radius limit (in miles).
*   `global_mode`: If `true` (or when running inside GitHub Actions), the script pulls all upcoming matching events globally, enabling the client-side location search on the website to find events from any address.
*   `lorcana_keywords` / `riftbound_keywords`: Specific keywords to filter for in event names/descriptions.

## How to Run

### Command Line Execution
```bash
python find_events.py
```
To run with command-line overrides (latitude, longitude, radius):
```bash
python find_events.py 28.2238 -82.4549 150
```

Once the script completes, open the generated report in your default web browser:
```bash
# On Windows
start events_report.html

# On macOS
open events_report.html

# On Linux
xdg-open events_report.html
```

---

## Weekly Scheduling Setup

To keep the dashboard updated automatically, you can set the script to run every week.

### On Windows
We provide an automated PowerShell setup script. Open a PowerShell window as **Administrator** and run:
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
.\schedule_task.ps1
```
This registers a Scheduled Task named `PlayhubEventFinder` that runs `run_weekly.bat` every **Sunday at 10:00 AM** in the background, writing updates silently to `events_report.html`.

### On macOS / Linux
You can register a `cron` job. Open your crontab manager:
```bash
crontab -e
```
Add the following line to run the script every Sunday at 10:00 AM (make sure to replace the path with your absolute repository path):
```text
0 10 * * 0 cd /path/to/playhub-event-finder && /usr/bin/python3 find_events.py > /dev/null 2>&1
```

### GitHub Actions & Pages Setup (Cloud Deployment)

If you would like to host the interactive report on **GitHub Pages** so that it can be viewed from anywhere:

1. **Push to GitHub:** Push your repository to GitHub. Ensure `config.json` and `index.html` are excluded (they are automatically ignored).
2. **Configure Settings (Optional):**
   - The GitHub Actions runner will use the default coordinates from `config.example.json` (or any coordinates you change in it) because dynamic IP-based geolocation is automatically bypassed in CI environments to prevent centering on the GitHub runner's server center.
   - Edit the coordinates/radius in `config.example.json` to configure the default view for the hosted version.
3. **Trigger the First Build:**
   - On GitHub, go to the **Actions** tab of your repository.
   - Select the **Deploy Playhub Event Finder** workflow.
   - Click **Run workflow** to trigger it manually. This will generate `index.html` and push it to a new `gh-pages` branch.
4. **Enable GitHub Pages:**
   - In your repository settings, select **Pages** from the sidebar.
   - Under **Build and deployment**, set the Source to **Deploy from a branch**.
   - Select the `gh-pages` branch and the `/ (root)` folder, then click **Save**.

The page will now be hosted publicly, and the GitHub Actions cron schedule will automatically rebuild and update it every Sunday at 10:00 AM UTC.

## Running Unit Tests

We use Python's built-in `unittest` library to verify distance calculations, keyword filtering, and config parsing. Run the tests using:
```bash
python test_events.py
```

## License
Licensed under the [MIT License](LICENSE).
