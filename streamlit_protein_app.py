import subprocess
subprocess.run(["playwright", "install", "chromium"], check=True)
import streamlit as st
import pandas as pd
import asyncio
import os
import json
import re
from datetime import datetime
import random
import sys
import traceback
import cloudscraper
from http.cookiejar import MozillaCookieJar
from playwright.async_api import async_playwright
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import zipfile
import io

# Page configuration
st.set_page_config(
    page_title="PhosphoSite Protein Details Scraper",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
CONFIG = {
    'headless': True,
    'max_retries': 3,
}

def get_random_delay():
    """Return a random delay between 1 and 3 seconds"""
    return random.uniform(1, 3)

async def handle_cloudflare_challenge(page):
    """Handle Cloudflare challenge if encountered"""
    try:
        if await page.query_selector("iframe[src*='challenges.cloudflare.com']"):
            st.info("Detected Cloudflare challenge, attempting to solve...")
            
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'mobile': False
                },
                delay=10
            )
            
            current_url = page.url
            response = scraper.get(current_url)
            
            if response.status_code == 200:
                st.success("Successfully bypassed Cloudflare")
                cookies = scraper.cookies.get_dict()
                
                for name, value in cookies.items():
                    await page.context.add_cookies([{
                        'name': name,
                        'value': value,
                        'url': current_url
                    }])
                
                await page.reload()
                await page.wait_for_load_state('networkidle', timeout=30000)
                return True
            else:
                st.error(f"Cloudscraper failed with status code: {response.status_code}")
                
        return False
            
    except Exception as e:
        st.error(f"Failed to handle Cloudflare challenge: {str(e)}")
        return False

async def add_random_behavior(page):
    """Add random human-like behavior"""
    try:
        for _ in range(random.randint(2, 5)):
            await page.mouse.move(
                random.randint(0, 800),
                random.randint(0, 600)
            )
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        await page.mouse.wheel(0, random.randint(100, 500))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.mouse.wheel(0, random.randint(-200, -100))
        
        await page.set_viewport_size({
            'width': random.randint(1050, 1920),
            'height': random.randint(800, 1080)
        })
        
        for _ in range(random.randint(1, 3)):
            await page.keyboard.press('Tab')
            await asyncio.sleep(random.uniform(0.1, 0.3))
            
    except Exception as e:
        st.warning(f"Error in random behavior: {str(e)}")

async def load_cookies(context, cookie_file='cookies.json'):
    """Load cookies from file if exists"""
    try:
        if os.path.exists(cookie_file):
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                await context.add_cookies(cookies)
                st.info(f"Loaded {len(cookies)} cookies")
    except Exception as e:
        st.warning(f"Error loading cookies: {str(e)}")

async def save_cookies(context, cookie_file='cookies.json'):
    """Save cookies to file"""
    try:
        cookies = await context.cookies()
        with open(cookie_file, 'w') as f:
            json.dump(cookies, f)
    except Exception as e:
        st.warning(f"Error saving cookies: {str(e)}")

def split_alt_names(alt_names_str):
    """Split alt names by semicolon and clean up"""
    if not alt_names_str:
        return []
    
    names = [name.strip() for name in alt_names_str.split(';')]
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
        
        if alt_names:
            alt_names_list = split_alt_names(alt_names)
            for alt_name in alt_names_list:
                exploded_data.append({
                    'Protein_ID': protein_id,
                    'PhosphoSite_Protein_Name': phosphosite_name,
                    'Alt_Name': alt_name,
                    'UniProt_ID': uniprot_id,
                    'Gene_Symbols': gene_symbols,
                    'Original_Alt_Names': alt_names
                })
        else:
            exploded_data.append({
                'Protein_ID': protein_id,
                'PhosphoSite_Protein_Name': phosphosite_name,
                'Alt_Name': None,
                'UniProt_ID': uniprot_id,
                'Gene_Symbols': gene_symbols,
                'Original_Alt_Names': None
            })
    
    return exploded_data

async def scrape_protein_details(protein_id, page, max_retries=3):
    """Scrape protein details including alt names, UniProt ID, gene symbols, and PhosphoSite+ protein name"""
    
    for attempt in range(max_retries):
        try:
            url = f"https://www.phosphosite.org/proteinAction.action?id={protein_id}&showAllSites=true"
            await page.goto(url)
            
            if await handle_cloudflare_challenge(page):
                await asyncio.sleep(random.uniform(5, 8))
            
            await add_random_behavior(page)
            await page.wait_for_load_state('domcontentloaded')
            
            no_record = await page.query_selector("p.noRecordFoundText")
            if no_record and "No Protein Record found !!" in await no_record.inner_text():
                st.error(f"Protein ID {protein_id}: No protein record found in database")
                return None
            
            # Extract PhosphoSite+ protein name from breadcrumb
            phosphosite_protein_name = None
            breadcrumb = await page.query_selector("#titleMainHeader")
            if breadcrumb:
                breadcrumb_text = await breadcrumb.inner_text()
                match = re.search(r">\s*Protein\s*>\s*([A-Za-z0-9_\-]+)", breadcrumb_text)
                if match:
                    phosphosite_protein_name = match.group(1).strip()
                    st.success(f"Extracted PhosphoSite+ protein name: {phosphosite_protein_name}")
            
            await asyncio.sleep(2)
            
            # Click the Protein Information tab
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
                        break
                except Exception:
                    continue
            
            if not info_tab:
                st.error("Could not find Protein Information tab")
                return None
            
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
            alt_names = None
            try:
                alt_span = await page.query_selector("xpath=//span[@class='bold02' and contains(text(), 'Alt. Names/Synonyms:')]")
                if alt_span:
                    parent_td = await alt_span.query_selector("xpath=..")
                    if parent_td:
                        full_text = await parent_td.inner_text()
                        alt_names = full_text.replace("Alt. Names/Synonyms:", "").strip()
                        st.success(f"Found Alt Names: {alt_names}")
            except Exception as e:
                st.warning(f"Could not extract Alt Names: {str(e)}")
            
            protein_data['Alt_Names'] = alt_names
            
            # Extract UniProt ID
            uniprot_id = None
            try:
                uniprot_link = await page.query_selector("xpath=//a[contains(@href, 'uniprot.org')]")
                if uniprot_link:
                    uniprot_id = await uniprot_link.inner_text()
                    st.success(f"Found UniProt ID: {uniprot_id}")
            except Exception as e:
                st.warning(f"Could not extract UniProt ID: {str(e)}")
            
            protein_data['UniProt_ID'] = uniprot_id
            
            # Extract Gene Symbols
            gene_symbols = None
            try:
                gene_span = await page.query_selector("xpath=//span[@class='bold02' and contains(text(), 'Gene Symbols:')]")
                if gene_span:
                    parent_td = await gene_span.query_selector("xpath=..")
                    if parent_td:
                        full_text = await parent_td.inner_text()
                        gene_symbols = full_text.replace("Gene Symbols:", "").strip()
                        st.success(f"Found Gene Symbols: {gene_symbols}")
            except Exception as e:
                st.warning(f"Could not extract Gene Symbols: {str(e)}")
            
            protein_data['Gene_Symbols'] = gene_symbols
            
            st.success(f"Protein ID {protein_id}: Successfully scraped protein details")
            return protein_data
            
        except Exception as e:
            st.error(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            return None

async def scrape_proteins_async(protein_ids, progress_bar, status_text):
    """Scrape multiple proteins asynchronously"""
    results = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=CONFIG['headless'],
                args=[
                    '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials', '--disable-web-security',
                    '--disable-setuid-sandbox', '--disable-webgl',
                    '--disable-threaded-animation', '--disable-threaded-scrolling',
                    '--disable-in-process-stack-traces', '--disable-histogram-customizer',
                    '--disable-extensions', '--metrics-recording-only',
                    '--no-first-run', '--password-store=basic', '--use-mock-keychain',
                    f'--window-size={random.randint(1050, 1920)},{random.randint(800, 1080)}',
                ]
            )
            
            browser_context = await browser.new_context(
                viewport={'width': random.randint(1050, 1920), 'height': random.randint(800, 1080)},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                locale='en-US', timezone_id='America/New_York',
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive', 'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none', 'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                    'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"macOS"'
                }
            )
            
            await load_cookies(browser_context)
            
            for i, protein_id in enumerate(protein_ids):
                try:
                    page = await browser_context.new_page()
                    page.set_default_timeout(30000)
                    page.set_default_navigation_timeout(30000)
                    
                    delay = random.uniform(3, 7)
                    await asyncio.sleep(delay)
                    
                    status_text.text(f"Processing Protein ID {protein_id}...")
                    result = await scrape_protein_details(protein_id, page)
                    
                    if result is not None:
                        results.append(result)
                    
                    await save_cookies(browser_context)
                    await add_random_behavior(page)
                    await page.close()
                    
                    progress_bar.progress((i + 1) / len(protein_ids))
                    
                except Exception as e:
                    st.error(f"Error processing Protein ID {protein_id}: {str(e)}")
                    continue
            
            await browser.close()
            
    except Exception as e:
        st.error(f"Fatal error: {str(e)}")
        return []
    
    return results

def create_visualizations(df):
    """Create visualizations for the scraped data"""
    if df.empty:
        return None
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Protein Distribution', 'Alt Names Count', 'Gene Symbols Distribution', 'UniProt IDs'),
        specs=[[{"type": "pie"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "scatter"}]]
    )
    
    # 1. Protein distribution pie chart
    protein_counts = df['PhosphoSite_Protein_Name'].value_counts()
    fig.add_trace(
        go.Pie(labels=protein_counts.index, values=protein_counts.values, name="Proteins"),
        row=1, col=1
    )
    
    # 2. Alt names count bar chart
    alt_names_counts = df['Alt_Name'].value_counts().head(10)
    fig.add_trace(
        go.Bar(x=alt_names_counts.index, y=alt_names_counts.values, name="Alt Names"),
        row=1, col=2
    )
    
    # 3. Gene symbols distribution
    gene_counts = df['Gene_Symbols'].value_counts().head(10)
    fig.add_trace(
        go.Bar(x=gene_counts.index, y=gene_counts.values, name="Gene Symbols"),
        row=2, col=1
    )
    
    # 4. UniProt IDs scatter (if available)
    if 'UniProt_ID' in df.columns and not df['UniProt_ID'].isna().all():
        uniprot_counts = df['UniProt_ID'].value_counts().head(10)
        fig.add_trace(
            go.Scatter(x=uniprot_counts.index, y=uniprot_counts.values, mode='markers', name="UniProt IDs"),
            row=2, col=2
        )
    
    fig.update_layout(height=800, title_text="Protein Details Analysis")
    return fig

def main():
    st.markdown('<h1 class="main-header">🧬 PhosphoSite Protein Details Scraper</h1>', unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("⚙️ Configuration")
    
    # Mode selection
    mode = st.sidebar.selectbox(
        "Select Mode",
        ["Single Protein", "Batch Processing", "Data Analysis"]
    )
    
    if mode == "Single Protein":
        st.header("🔍 Single Protein Scraping")
        
        col1, col2 = st.columns(2)
        
        with col1:
            protein_id = st.number_input("Enter Protein ID", min_value=1, value=1035, step=1)
        
        with col2:
            if st.button("🚀 Scrape Protein", type="primary"):
                if protein_id:
                    with st.spinner("Scraping protein details..."):
                        try:
                            # Run the scraping
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                            async def run_single_scrape():
                                async with async_playwright() as p:
                                    browser = await p.chromium.launch(headless=CONFIG['headless'])
                                    context = await browser.new_context()
                                    page = await context.new_page()
                                    
                                    result = await scrape_protein_details(protein_id, page)
                                    await browser.close()
                                    return result
                            
                            result = loop.run_until_complete(run_single_scrape())
                            loop.close()
                            
                            if result:
                                st.success("✅ Scraping completed successfully!")
                                
                                # Display results
                                st.subheader("📊 Scraped Data")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Protein ID", result['Protein_ID'])
                                with col2:
                                    st.metric("PhosphoSite Name", result['PhosphoSite_Protein_Name'])
                                with col3:
                                    st.metric("UniProt ID", result['UniProt_ID'] or "N/A")
                                with col4:
                                    st.metric("Gene Symbols", result['Gene_Symbols'] or "N/A")
                                
                                # Show alt names
                                if result['Alt_Names']:
                                    st.subheader("🔄 Alternative Names")
                                    alt_names_list = split_alt_names(result['Alt_Names'])
                                    for i, name in enumerate(alt_names_list, 1):
                                        st.write(f"{i}. {name}")
                                
                                # Create exploded DataFrame
                                exploded_data = explode_alt_names_data([result])
                                df = pd.DataFrame(exploded_data)
                                
                                st.subheader("📋 Data Table")
                                st.dataframe(df, use_container_width=True)
                                
                                # Download button
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download CSV",
                                    data=csv,
                                    file_name=f"{result['PhosphoSite_Protein_Name']}_details_exploded.csv",
                                    mime="text/csv"
                                )
                                
                            else:
                                st.error("❌ Failed to scrape protein details")
                                
                        except Exception as e:
                            st.error(f"❌ Error during scraping: {str(e)}")
    
    elif mode == "Batch Processing":
        st.header("📦 Batch Processing")
        
        # Input method selection
        input_method = st.selectbox(
            "Select Input Method",
            ["Range", "List", "Upload CSV"]
        )
        
        protein_ids = []
        
        if input_method == "Range":
            col1, col2 = st.columns(2)
            with col1:
                start_id = st.number_input("Start Protein ID", min_value=1, value=1035, step=1)
            with col2:
                end_id = st.number_input("End Protein ID", min_value=start_id, value=1035, step=1)
            
            if st.button("🚀 Start Batch Scraping", type="primary"):
                protein_ids = list(range(start_id, end_id + 1))
        
        elif input_method == "List":
            protein_list = st.text_area(
                "Enter Protein IDs (one per line or comma-separated)",
                value="1035,1036,1037",
                help="Enter protein IDs separated by commas or new lines"
            )
            
            if st.button("🚀 Start Batch Scraping", type="primary"):
                # Parse input
                if protein_list:
                    # Split by comma or newline
                    ids = protein_list.replace('\n', ',').split(',')
                    protein_ids = [int(id.strip()) for id in ids if id.strip().isdigit()]
        
        elif input_method == "Upload CSV":
            uploaded_file = st.file_uploader("Upload CSV file with Protein IDs", type=['csv'])
            
            if uploaded_file is not None:
                try:
                    df_upload = pd.read_csv(uploaded_file)
                    if 'Protein_ID' in df_upload.columns:
                        protein_ids = df_upload['Protein_ID'].tolist()
                        st.success(f"Loaded {len(protein_ids)} protein IDs from CSV")
                    else:
                        st.error("CSV must contain a 'Protein_ID' column")
                except Exception as e:
                    st.error(f"Error reading CSV: {str(e)}")
            
            if st.button("🚀 Start Batch Scraping", type="primary") and protein_ids:
                pass
        
        # Batch processing
        if protein_ids:
            st.info(f"📋 Processing {len(protein_ids)} proteins: {protein_ids[:5]}{'...' if len(protein_ids) > 5 else ''}")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            if st.button("🚀 Start Scraping", type="primary"):
                with st.spinner("Scraping proteins..."):
                    try:
                        # Run async scraping
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        results = loop.run_until_complete(scrape_proteins_async(protein_ids, progress_bar, status_text))
                        loop.close()
                        
                        if results:
                            st.success(f"✅ Successfully scraped {len(results)} proteins!")
                            
                            # Create exploded DataFrame
                            exploded_data = explode_alt_names_data(results)
                            df = pd.DataFrame(exploded_data)
                            
                            st.subheader("📊 Results Summary")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Proteins Scraped", len(results))
                            with col2:
                                st.metric("Total Alt Names", len(df))
                            with col3:
                                st.metric("Unique Proteins", df['PhosphoSite_Protein_Name'].nunique())
                            
                            st.subheader("📋 Data Preview")
                            st.dataframe(df.head(10), use_container_width=True)
                            
                            # Download options
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download CSV",
                                    data=csv,
                                    file_name=f"batch_proteins_details_exploded.csv",
                                    mime="text/csv"
                                )
                            
                            with col2:
                                # Create ZIP file with individual protein files
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                                    for result in results:
                                        protein_name = result.get('PhosphoSite_Protein_Name', f"Protein_{result['Protein_ID']}")
                                        protein_exploded_data = explode_alt_names_data([result])
                                        protein_df = pd.DataFrame(protein_exploded_data)
                                        csv_data = protein_df.to_csv(index=False)
                                        zip_file.writestr(f"{protein_name}_details_exploded.csv", csv_data)
                                
                                st.download_button(
                                    label="📦 Download ZIP",
                                    data=zip_buffer.getvalue(),
                                    file_name="protein_details_individual_files.zip",
                                    mime="application/zip"
                                )
                            
                            # Visualizations
                            st.subheader("📈 Data Visualizations")
                            fig = create_visualizations(df)
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        
                        else:
                            st.error("❌ No data was scraped successfully")
                    
                    except Exception as e:
                        st.error(f"❌ Error during batch scraping: {str(e)}")
    
    elif mode == "Data Analysis":
        st.header("📊 Data Analysis")
        
        uploaded_file = st.file_uploader("Upload CSV file for analysis", type=['csv'])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.success(f"✅ Loaded data with {len(df)} rows")
                
                st.subheader("📋 Data Overview")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Rows", len(df))
                with col2:
                    st.metric("Unique Proteins", df['PhosphoSite_Protein_Name'].nunique())
                with col3:
                    st.metric("Unique Alt Names", df['Alt_Name'].nunique())
                with col4:
                    st.metric("Unique Gene Symbols", df['Gene_Symbols'].nunique())
                
                st.subheader("📊 Data Preview")
                st.dataframe(df.head(20), use_container_width=True)
                
                # Visualizations
                st.subheader("📈 Data Visualizations")
                fig = create_visualizations(df)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Statistics
                st.subheader("📊 Statistics")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Top 10 Alternative Names:**")
                    top_alt_names = df['Alt_Name'].value_counts().head(10)
                    st.dataframe(top_alt_names.reset_index().rename(columns={'index': 'Alt Name', 'Alt_Name': 'Count'}))
                
                with col2:
                    st.write("**Top 10 Gene Symbols:**")
                    top_genes = df['Gene_Symbols'].value_counts().head(10)
                    st.dataframe(top_genes.reset_index().rename(columns={'index': 'Gene Symbol', 'Gene_Symbols': 'Count'}))
                
            except Exception as e:
                st.error(f"❌ Error loading CSV: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🧬 PhosphoSite Protein Details Scraper | Built with Streamlit and Playwright</p>
            <p>For research purposes only. Please respect PhosphoSitePlus terms of service.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main() 