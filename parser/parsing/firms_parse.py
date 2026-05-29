# pyright: standard
import random
from playwright.sync_api import sync_playwright
import time
import json
from pathlib import Path
from urllib.parse import urlparse

def save_2gis_api_requests(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Create directory for API responses
        output_dir = Path('firms')
        output_dir.mkdir(exist_ok=True)

        # Handle incoming responses that contains JSONs of branches of restaraunts, fast-foods, cafe and etc.
        def handle_response(response):
            try:
                if response.url.startswith('https://catalog.api.2gis.ru/'):
                    parsed = urlparse(response.url)

                    # Filename based on what page we are parsing
                    filename = "page_1.json"
                    try:
                      filename = f"page_{parsed.query.split('page=')[1].split('&')[0]}.json"
                    except:
                      pass

                    # Process different response types, but there are usually only JSON
                    content_type = response.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        data = response.json()
                    else:
                        data = {'raw_content': response.text()}

                    # Save metadata along with response
                    full_data = {
                        'request_url': response.url,
                        'request_method': response.request.method,
                        'status': response.status,
                        'headers': dict(response.headers),
                        'timing': response.request.timing,
                        'body': data
                    }

                    # Save to file
                    with open(output_dir / filename, 'w', encoding='utf-8') as f:
                        json.dump(full_data, f, indent=2, ensure_ascii=False)

                    print(f"Saved API response: {filename}")
            except Exception as e:
                print(f"Error processing {response.url}: {str(e)}")

        # Monitor responses
        page.on('response', handle_response)

        # Navigate to the page
        page.goto(url, wait_until='networkidle')

        current_page = 1
        max_pages = 1000  # Safety limit - adjust as needed

        while current_page <= max_pages:
            time.sleep(0.5 + random.random())
            print(f"Processing page {current_page}")

            try:
                # Find the next page button (current page + 1)
                next_page_btn = page.get_by_role("link", name=str(current_page+1), exact=True)
                if next_page_btn.count() == 0:
                    print("Reached last page")
                    break

                # Scroll to and click the button
                next_page_btn.scroll_into_view_if_needed()
                next_page_btn.click()

                # Wait for new content to load
                page.wait_for_load_state('networkidle')
                time.sleep(1)  # Additional buffer

                current_page += 1
            except Exception as e:
                print(f"Error navigating to page {current_page + 1}: {e}")
                break        # Keep browser open for manual interaction if needed

        print("Browser is open - interact with the page as needed...")
        print("Press Enter in this terminal when done...")
        input()

        browser.close()

save_2gis_api_requests("https://2gis.kz/almaty/search/Поесть")
