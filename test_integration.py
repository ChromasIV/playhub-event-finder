import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def run_test():
    async with async_playwright() as p:
        # Launch browser headlessly with web security disabled to allow local file:// pages to fetch mocked APIs
        print("Launching headless Chromium...")
        browser = await p.chromium.launch(headless=True, args=["--disable-web-security"])
        page = await browser.new_page()
        
        # Capture browser console outputs and uncaught errors to standard output/error for CI diagnostics
        page.on("console", lambda msg: print(f"BROWSER CONSOLE: [{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"BROWSER ERROR: {err}", file=sys.stderr))
        
        # Get absolute URI of index.html cross-platform
        file_url = Path(os.path.abspath("index.html")).as_uri()
        print(f"Loading page: {file_url}")
        
        # Intercept and mock Nominatim geocoding requests to avoid live network rate-limits in CI environment
        await page.route("**/nominatim.openstreetmap.org/search*", lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='[{"lat":"27.9506","lon":"-82.4572","display_name":"Tampa, FL, USA"}]' if "Tampa" in route.request.url else
                 '[{"lat":"0.0","lon":"0.0","display_name":"Seattle, WA, USA"}]'
        ))
        
        await page.goto(file_url)
        
        # Verify page title
        title = await page.title()
        print(f"Page title: {title}")
        assert "Playhub Weekly Event Matcher" in title, "Title mismatch!"
        
        # Wait for events to render initially
        await page.wait_for_selector("#lorcana-container")
        
        # Get initial event counts
        lorcana_initial_text = await page.locator("#lorcana-count").text_content()
        riftbound_initial_text = await page.locator("#riftbound-count").text_content()
        print(f"Initial counts: Lorcana={lorcana_initial_text}, Riftbound={riftbound_initial_text}")
        
        # 1. Test Date Range Filter
        print("Testing Date Filter (Next 7 Days)...")
        await page.select_option("#date-filter", "7")
        # Give JS a moment to filter and render
        await page.wait_for_timeout(500)
        
        lorcana_filtered_text = await page.locator("#lorcana-count").text_content()
        riftbound_filtered_text = await page.locator("#riftbound-count").text_content()
        print(f"Filtered (7 Days) counts: Lorcana={lorcana_filtered_text}, Riftbound={riftbound_filtered_text}")
        
        # Verify that counts changed or stayed valid
        assert "Found" in lorcana_filtered_text, "Lorcana filtered text invalid"
        
        # Reset date filter to all
        await page.select_option("#date-filter", "all")
        await page.wait_for_timeout(500)
        
        # 2. Test Geocoding and distance filter (Tampa, FL baseline)
        print("Testing Location Search: Tampa, FL (establishing baseline)...")
        await page.fill("#location-input", "Tampa, FL")
        await page.click("#location-search-btn")
        
        await page.wait_for_selector("#location-status:has-text('Location updated successfully!')", timeout=10000)
        
        lorcana_tampa_baseline = await page.locator("#lorcana-count").text_content()
        riftbound_tampa_baseline = await page.locator("#riftbound-count").text_content()
        print(f"Tampa baseline counts: Lorcana={lorcana_tampa_baseline}, Riftbound={riftbound_tampa_baseline}")
        
        # 3. Test Location Search: Seattle, WA (should hide Florida events)
        print("Testing Location Search: Seattle, WA...")
        await page.fill("#location-input", "Seattle, WA")
        await page.click("#location-search-btn")
        
        # Wait for the status indicator to show success
        await page.wait_for_selector("#location-status:has-text('Location updated successfully!')", timeout=10000)
        
        center_text = await page.locator("#center-display-name").text_content()
        print(f"New Search Center: {center_text}")
        assert "Seattle" in center_text, f"Center text didn't update to Seattle: {center_text}"
        
        lorcana_seattle_text = await page.locator("#lorcana-count").text_content()
        riftbound_seattle_text = await page.locator("#riftbound-count").text_content()
        print(f"Seattle counts: Lorcana={lorcana_seattle_text}, Riftbound={riftbound_seattle_text}")
        
        # In Seattle, Florida events (within 100 or 500 miles) should be 0 since Seattle is 2500 miles away.
        assert "0 Found" in lorcana_seattle_text, f"Lorcana events were not filtered out! {lorcana_seattle_text}"
        assert "0 Found" in riftbound_seattle_text, f"Riftbound events were not filtered out! {riftbound_seattle_text}"
        
        # 4. Test returning to Tampa, FL
        print("Testing Location Search: Tampa, FL (restoring baseline)...")
        await page.fill("#location-input", "Tampa, FL")
        await page.click("#location-search-btn")
        
        await page.wait_for_selector("#location-status:has-text('Location updated successfully!')", timeout=10000)
        
        lorcana_tampa_text = await page.locator("#lorcana-count").text_content()
        riftbound_tampa_text = await page.locator("#riftbound-count").text_content()
        print(f"Tampa counts: Lorcana={lorcana_tampa_text}, Riftbound={riftbound_tampa_text}")
        
        # Tampa events should reappear and match the baseline exactly
        assert lorcana_tampa_text == lorcana_tampa_baseline, f"Lorcana counts did not restore! {lorcana_tampa_text} vs {lorcana_tampa_baseline}"
        assert riftbound_tampa_text == riftbound_tampa_baseline, f"Riftbound counts did not restore! {riftbound_tampa_text} vs {riftbound_tampa_baseline}"
        
        print("All automated integration tests passed successfully!")
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"Test failed: {e}", file=sys.stderr)
        sys.exit(1)
