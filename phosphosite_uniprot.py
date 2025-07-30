from playwright.async_api import async_playwright
import pandas as pd
import time
import os
import json
import re
from datetime import datetime
import random
import sys
import traceback
import asyncio
import cloudscraper
from http.cookiejar import MozillaCookieJar

# Configuration
CONFIG = {
    'headless': True,  # Run in headless mode for better performance
    'start_protein_id': 1035,  # Starting protein ID
    'end_protein_id': 1035,  # Ending protein ID
    'max_retries': 3,  # Maximum number of retries per protein
}

def get_random_delay():
    """Return a random delay between 1 and 3 seconds"""
    return random.uniform(1, 3)

async def handle_cloudflare_challenge(page):
    """Handle Cloudflare challenge if encountered"""
    try:
        # Check for Cloudflare challenge
        if await page.query_selector("iframe[src*='challenges.cloudflare.com']"):
            print("[DEBUG] Detected Cloudflare challenge, attempting to solve...")
            
            # Create a cloudscraper session
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'mobile': False
                },
                delay=10
            )
            
            # Get the current URL
            current_url = page.url
            
            # Try to get the page using cloudscraper
            print("[DEBUG] Using cloudscraper to bypass challenge...")
            response = scraper.get(current_url)
            
            if response.status_code == 200:
                print("[DEBUG] Successfully bypassed Cloudflare")
                # Extract cookies from cloudscraper session
                cookies = scraper.cookies.get_dict()
                
                # Add cookies to playwright context
                for name, value in cookies.items():
                    await page.context.add_cookies([{
                        'name': name,
                        'value': value,
                        'url': current_url
                    }])
                
                # Reload the page with the new cookies
                await page.reload()
                await page.wait_for_load_state('networkidle', timeout=30000)
                return True
            else:
                print(f"[DEBUG] Cloudscraper failed with status code: {response.status_code}")
                
        return False
            
    except Exception as e:
        print(f"[ERROR] Failed to handle Cloudflare challenge: {str(e)}")
        traceback.print_exc()
    return False

async def add_random_behavior(page):
    """Add random human-like behavior"""
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            await page.mouse.move(
                random.randint(0, 800),
                random.randint(0, 600)
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Random scrolling
        await page.mouse.wheel(0, random.randint(100, 500))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.mouse.wheel(0, random.randint(-200, -100))
        
        # Random viewport changes
        await page.set_viewport_size({
            'width': random.randint(1050, 1920),
            'height': random.randint(800, 1080)
        })
        
        # Simulate random key presses (tab, arrow keys)
        for _ in range(random.randint(1, 3)):
            await page.keyboard.press('Tab')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
    except Exception as e:
        print(f"[WARNING] Error in random behavior: {str(e)}")

async def load_cookies(context, cookie_file='cookies.json'):
    """Load cookies from file if exists"""
    try:
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                print(f"[DEBUG] Loaded {len(cookies)} cookies")
    except Exception as e:
        print(f"[WARNING] Error loading cookies: {str(e)}")

async def save_cookies(context, cookie_file='cookies.json'):
    """Save cookies to file"""
    try:
        cookies = await context.cookies()
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)
            print(f"[DEBUG] Saved {len(cookies)} cookies")
    except Exception as e:
        print(f"[WARNING] Error saving cookies: {str(e)}")

async def scrape_protein_details(protein_id, page, max_retries=3):
    """Scrape protein details including alt names, UniProt ID, gene symbols, and PhosphoSite+ protein name"""
    
    for attempt in range(max_retries):
        try:
            # Navigate to the protein page
            url = f"https://www.phosphosite.org/proteinAction.action?id={protein_id}&showAllSites=true"
            await page.goto(url)
            
            # Check for Cloudflare
            if await handle_cloudflare_challenge(page):
                await asyncio.sleep(random.uniform(5, 8))
            
            await add_random_behavior(page)
            
            # Wait for page to load
            await page.wait_for_load_state('domcontentloaded')
            
            # Check if protein exists
            no_record = await page.query_selector("p.noRecordFoundText")
            if no_record and "No Protein Record found !!" in await no_record.inner_text():
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Protein ID {protein_id}: No protein record found in database")
                return None
            
            print(f"[DEBUG] Protein exists!")
            
            # Extract PhosphoSite+ protein name from breadcrumb
            phosphosite_protein_name = None
            breadcrumb = await page.query_selector("#titleMainHeader")
            if breadcrumb:
                breadcrumb_text = await breadcrumb.inner_text()
                # Extract the protein name after "Protein >"
                match = re.search(r">\s*Protein\s*>\s*([A-Za-z0-9_\-]+)", breadcrumb_text)
                if match:
                    phosphosite_protein_name = match.group(1).strip()
                    print(f"[DEBUG] Extracted PhosphoSite+ protein name: {phosphosite_protein_name}")
            
            # Wait before looking for Protein Information tab
            print("[DEBUG] Waiting 2 seconds before looking for Protein Information tab...")
            await asyncio.sleep(2)
            
            # Click the Protein Information tab
            print("[DEBUG] Looking for Protein Information tab...")
            info_tab_selectors = [
                "xpath=//*[@id='tabs1']/ul/li[1]/a",
                "xpath=//a[contains(text(), 'Protein Information')]",
                "xpath=//a[contains(@href, 'proteinInfo')]",
                "css=a[href*='proteinInfo']",
                "css=a:has-text('Protein Information')"
            ]
            
            info_tab = None
            for selector in info_tab_selectors:
                try:
                    info_tab = await page.query_selector(selector)
                    if info_tab:
                        print(f"[DEBUG] Found Protein Information tab using selector: {selector}")
                        break
                except Exception as e:
                    print(f"[DEBUG] Selector {selector} failed: {str(e)}")
                    continue
            
            if not info_tab:
                print("[ERROR] Could not find Protein Information tab")
                return None
            
            print("[DEBUG] Clicking Protein Information tab...")
            await info_tab.click()
            await asyncio.sleep(3)
            
            # Initialize data dictionary
            protein_data = {
                'Protein_ID': protein_id,
                'PhosphoSite_Protein_Name': phosphosite_protein_name,
                'Alt_Names': None,
                'UniProt_ID': None,
                'Gene_Symbols': None
            }
            
            # Extract Alt Names/Synonyms
            print("[DEBUG] Looking for Alt Names/Synonyms...")
            alt_names_selectors = [
                "xpath=//span[contains(text(), 'Alt. Names/Synonyms:')]/following-sibling::text()",
                "xpath=//span[@class='bold02' and contains(text(), 'Alt. Names/Synonyms:')]/following-sibling::text()",
                "xpath=//td[contains(.//span, 'Alt. Names/Synonyms:')]/text()[2]",
                "css=span.bold02:contains('Alt. Names/Synonyms:') + *"
            ]
            
            alt_names = None
            for selector in alt_names_selectors:
                try:
                    # Try to find the span with Alt Names
                    alt_span = await page.query_selector("xpath=//span[@class='bold02' and contains(text(), 'Alt. Names/Synonyms:')]")
                    if alt_span:
                        # Get the parent td element
                        parent_td = await alt_span.query_selector("xpath=..")
                        if parent_td:
                            full_text = await parent_td.inner_text()
                            # Remove the "Alt. Names/Synonyms:" part
                            alt_names = full_text.replace("Alt. Names/Synonyms:", "").strip()
                            print(f"[DEBUG] Found Alt Names: {alt_names}")
                            break
                except Exception as e:
                    print(f"[DEBUG] Alt names selector {selector} failed: {str(e)}")
                    continue
            
            protein_data['Alt_Names'] = alt_names
            
            # Extract UniProt ID
            print("[DEBUG] Looking for UniProt ID...")
            uniprot_selectors = [
                "xpath=//span[contains(text(), 'Reference #:')]/following-sibling::a",
                "xpath=//span[@class='bold02' and contains(text(), 'Reference #:')]/following-sibling::a",
                "xpath=//a[contains(@href, 'uniprot.org')]",
                "css=a[href*='uniprot.org']"
            ]
            
            uniprot_id = None
            for selector in uniprot_selectors:
                try:
                    uniprot_link = await page.query_selector(selector)
                    if uniprot_link:
                        uniprot_id = await uniprot_link.inner_text()
                        print(f"[DEBUG] Found UniProt ID: {uniprot_id}")
                        break
                except Exception as e:
                    print(f"[DEBUG] UniProt selector {selector} failed: {str(e)}")
                    continue
            
            protein_data['UniProt_ID'] = uniprot_id
            
            # Extract Gene Symbols
            print("[DEBUG] Looking for Gene Symbols...")
            gene_symbols_selectors = [
                "xpath=//span[contains(text(), 'Gene Symbols:')]/following-sibling::text()",
                "xpath=//span[@class='bold02' and contains(text(), 'Gene Symbols:')]/following-sibling::text()",
                "xpath=//td[contains(.//span, 'Gene Symbols:')]/text()[2]"
            ]
            
            gene_symbols = None
            for selector in gene_symbols_selectors:
                try:
                    # Try to find the span with Gene Symbols
                    gene_span = await page.query_selector("xpath=//span[@class='bold02' and contains(text(), 'Gene Symbols:')]")
                    if gene_span:
                        # Get the parent td element
                        parent_td = await gene_span.query_selector("xpath=..")
                        if parent_td:
                            full_text = await parent_td.inner_text()
                            # Remove the "Gene Symbols:" part
                            gene_symbols = full_text.replace("Gene Symbols:", "").strip()
                            print(f"[DEBUG] Found Gene Symbols: {gene_symbols}")
                            break
                except Exception as e:
                    print(f"[DEBUG] Gene symbols selector {selector} failed: {str(e)}")
                    continue
            
            protein_data['Gene_Symbols'] = gene_symbols
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Protein ID {protein_id}: Successfully scraped protein details")
            return protein_data
            
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            return None

def split_alt_names(alt_names_str):
    """Split alt names by semicolon and clean up"""
    if not alt_names_str:
        return []
    
    # Split by semicolon and clean up each name
    names = [name.strip() for name in alt_names_str.split(';')]
    # Remove any empty strings
    names = [name for name in names if name]
    return names

def explode_alt_names_data(data_list):
    """Explode alt names into separate rows"""
    exploded_data = []
    
    for protein_data in data_list:
        protein_id = protein_data['Protein_ID']
        phosphosite_name = protein_data['PhosphoSite_Protein_Name']
        uniprot_id = protein_data['UniProt_ID']
        gene_symbols = protein_data['Gene_Symbols']
        alt_names = protein_data['Alt_Names']
        
        # Split alt names
        if alt_names:
            alt_names_list = split_alt_names(alt_names)
            for alt_name in alt_names_list:
                exploded_data.append({
                    'Protein_ID': protein_id,
                    'PhosphoSite_Protein_Name': phosphosite_name,
                    'Alt_Name': alt_name,
                    'UniProt_ID': uniprot_id,
                    'Gene_Symbols': gene_symbols,
                    'Original_Alt_Names': alt_names  # Keep original for reference
                })
        else:
            # If no alt names, create one row with None
            exploded_data.append({
                'Protein_ID': protein_id,
                'PhosphoSite_Protein_Name': phosphosite_name,
                'Alt_Name': None,
                'UniProt_ID': uniprot_id,
                'Gene_Symbols': gene_symbols,
                'Original_Alt_Names': None
            })
    
    return exploded_data

async def main():
    # Create output directory if it doesn't exist
    output_dir = "protein_details_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a logs directory if it doesn't exist
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create a new log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(logs_dir, f'protein_details_scraping_log_{timestamp}.txt')
    
    # Check for resume point
    start_id = CONFIG['start_protein_id']
    end_id = CONFIG['end_protein_id']
    
    # Write header to log file
    with open(log_file, 'w') as f:
        f.write(f"Protein Details Scraping Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Starting from Protein ID: {start_id}\n")
        f.write("=" * 80 + "\n\n")
    
    try:
        async with async_playwright() as p:
            all_results = []
            
            # Create persistent context for cookies
            browser_context = None
            
            # Iterate through protein IDs
            for protein_id in range(start_id, CONFIG['end_protein_id'] + 1):
                user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                
                try:
                    # Launch browser with enhanced anti-detection settings
                    browser = await p.chromium.launch(
                        headless=CONFIG['headless'],
                        args=[
                            '--disable-gpu',
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-features=IsolateOrigins,site-per-process',
                            '--disable-site-isolation-trials',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins',
                            '--disable-site-isolation-trials',
                            '--disable-setuid-sandbox',
                            '--disable-webgl',
                            '--disable-threaded-animation',
                            '--disable-threaded-scrolling',
                            '--disable-in-process-stack-traces',
                            '--disable-histogram-customizer',
                            '--disable-extensions',
                            '--metrics-recording-only',
                            '--no-first-run',
                            '--password-store=basic',
                            '--use-mock-keychain',
                            f'--window-size={random.randint(1050, 1920)},{random.randint(800, 1080)}',
                        ]
                    )
                    
                    # Create or reuse context
                    if not browser_context:
                        browser_context = await browser.new_context(
                            viewport={'width': random.randint(1050, 1920), 'height': random.randint(800, 1080)},
                            user_agent=user_agent,
                            locale='en-US',
                            timezone_id='America/New_York',
                            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                            permissions=['geolocation'],
                            extra_http_headers={
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'Connection': 'keep-alive',
                                'Upgrade-Insecure-Requests': '1',
                                'Sec-Fetch-Dest': 'document',
                                'Sec-Fetch-Mode': 'navigate',
                                'Sec-Fetch-Site': 'none',
                                'Sec-Fetch-User': '?1',
                                'Cache-Control': 'max-age=0',
                                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                                'sec-ch-ua-mobile': '?0',
                                'sec-ch-ua-platform': '"macOS"'
                            }
                        )
                        await load_cookies(browser_context)
                    
                    page = await browser_context.new_page()
                    
                    # Add additional page configurations
                    page.set_default_timeout(30000)
                    page.set_default_navigation_timeout(30000)
                    
                    # Add random delays and behaviors between requests
                    delay = random.uniform(3, 7)
                    print(f"[DEBUG] Adding random delay of {delay:.2f} seconds between requests")
                    await asyncio.sleep(delay)
                    
                    # Process the protein
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting Protein ID {protein_id}")
                    
                    result = await scrape_protein_details(protein_id, page)
                    
                    if result is not None:
                        all_results.append(result)
                        print(f"[DEBUG] Added protein data to all_results. Current count: {len(all_results)}")
                    
                    # Save cookies after successful request
                    await save_cookies(browser_context)
                    
                    # Add random behavior between requests
                    await add_random_behavior(page)
                    
                    # Write to log file
                    with open(log_file, 'a') as f:
                        status = "Success" if result is not None else "No data"
                        protein_name = result.get('PhosphoSite_Protein_Name', f"Protein_{protein_id}") if result else f"Protein_{protein_id}"
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] Protein ID {protein_id} ({protein_name}): {status}\n")
                    
                except Exception as e:
                    error_msg = f"Error processing Protein ID {protein_id}: {str(e)}\n{traceback.format_exc()}"
                    print(error_msg)
                    with open(log_file, 'a') as f:
                        f.write(f"\n{error_msg}\n")
                    
                    if isinstance(e, (TimeoutError, ConnectionError)):
                        continue
                
                finally:
                    try:
                        if page:
                            await page.close()
                        if browser and browser_context != browser.contexts[0]:
                            await browser.close()
                    except Exception:
                        pass
            
            # Combine all results and save
            if all_results:
                print(f"[DEBUG] Number of results to combine: {len(all_results)}")
                try:
                    # Explode alt names
                    exploded_data = explode_alt_names_data(all_results)
                    df_exploded = pd.DataFrame(exploded_data)
                    print(f"[DEBUG] Exploded DataFrame shape: {df_exploded.shape}")
                    
                    # Save exploded individual protein files
                    for result in all_results:
                        protein_name = result.get('PhosphoSite_Protein_Name', f"Protein_{result['Protein_ID']}")
                        exploded_individual_path = os.path.join(output_dir, f'{protein_name}_details_exploded.csv')
                        
                        # Get exploded data for this protein
                        protein_exploded_data = explode_alt_names_data([result])
                        exploded_individual_df = pd.DataFrame(protein_exploded_data)
                        exploded_individual_df.to_csv(exploded_individual_path, index=False)
                        print(f"[DEBUG] Saved exploded individual data to: {exploded_individual_path}")
                    
                    # Save exploded combined file
                    combined_exploded_path = os.path.join(output_dir, f'all_proteins_details_exploded_{protein_name}.csv')
                    df_exploded.to_csv(combined_exploded_path, index=False)
                    print(f"[DEBUG] Saved exploded combined data to: {combined_exploded_path}")
                    
                    completion_msg = f"\nProtein Details Scraping completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    completion_msg += f"Total proteins processed: {len(all_results)}\n"
                    completion_msg += f"Exploded combined data saved to: {combined_exploded_path}"
                    print(completion_msg)
                    with open(log_file, 'a') as f:
                        f.write("\n" + "=" * 80 + "\n")
                        f.write(completion_msg)
                except Exception as e:
                    print(f"[ERROR] Failed to save combined CSV: {str(e)}")
                    traceback.print_exc()
            else:
                print("[DEBUG] No results to combine into CSV - all_results is empty")
                with open(log_file, 'a') as f:
                    f.write("\n[WARNING] No results to combine into CSV - all_results is empty\n")
    except Exception as e:
        error_msg = f"Fatal error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        with open(log_file, 'a') as f:
            f.write(f"\n{error_msg}\n")
        raise

if __name__ == "__main__":
    asyncio.run(main())
