# 🧬 PhosphoSite Protein Details Scraper

A comprehensive web scraping tool for extracting protein details from PhosphoSitePlus, including alternative names, UniProt IDs, gene symbols, and PhosphoSite+ protein names. Features both command-line and Streamlit web interface options.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Data Structure](#data-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)
- [Contributing](#contributing)

## 🎯 Overview

This project provides automated web scraping capabilities for PhosphoSitePlus, a comprehensive database of protein phosphorylation sites. The scraper extracts detailed protein information including:

- **PhosphoSite+ Protein Names**: Official protein identifiers from PhosphoSitePlus
- **Alternative Names/Synonyms**: All known alternative names for each protein
- **UniProt IDs**: Cross-references to UniProt database
- **Gene Symbols**: Official gene symbols and identifiers

### Key Capabilities

- **Single Protein Scraping**: Extract data for individual proteins by ID
- **Batch Processing**: Process multiple proteins simultaneously
- **Data Explosion**: Automatically splits alternative names into separate rows
- **Web Interface**: User-friendly Streamlit app for interactive scraping
- **Data Analysis**: Built-in visualizations and statistics

## ✨ Features

### 🔍 Web Scraping Features
- **Anti-Detection Measures**: Uses Playwright with stealth techniques
- **Cloudflare Bypass**: Handles Cloudflare challenges automatically
- **Cookie Management**: Saves and reuses cookies for better performance
- **Random Delays**: Implements human-like browsing behavior
- **Error Recovery**: Automatic retry mechanisms for failed requests

### 📊 Data Extraction
- **PhosphoSite+ Names**: Official protein identifiers from breadcrumb navigation
- **Alternative Names**: Complete list of synonyms and alternative names
- **UniProt Cross-references**: Direct links to UniProt database entries
- **Gene Symbols**: Official gene symbols and identifiers
- **Data Explosion**: Automatic splitting of alternative names into separate rows

### 🎨 User Interface
- **Streamlit Web App**: Interactive web interface
- **Progress Tracking**: Real-time progress indicators
- **Data Visualization**: Built-in charts and statistics
- **Download Options**: Multiple export formats (CSV, ZIP)
- **Error Handling**: User-friendly error messages

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Quick Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd streamlit_protein_name
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Install Playwright browsers**:
```bash
playwright install chromium
```

### Manual Installation

If you prefer manual installation:

```bash
pip install playwright pandas streamlit cloudscraper plotly
playwright install chromium
```

## 📖 Usage

### Command Line Usage

#### Single Protein Scraping
```bash
cd streamlit_protein_name
python phosphosite_uniprot.py
```

#### Configuration
Edit the configuration in `phosphosite_uniprot.py`:
```python
CONFIG = {
    'headless': True,  # Set to False for debugging
    'start_protein_id': 1035,  # Starting protein ID
    'end_protein_id': 1035,  # Ending protein ID
    'max_retries': 3,  # Maximum retries per protein
}
```

### Streamlit Web Interface

#### Launch the Web App
```bash
cd streamlit_protein_name
streamlit run streamlit_protein_app.py
```

#### Web App Features

1. **Single Protein Mode**:
   - Enter a protein ID (e.g., 1035)
   - Click "Scrape Protein"
   - View results and download exploded CSV

2. **Batch Processing Mode**:
   - **Range**: Specify start and end protein IDs
   - **List**: Enter comma-separated protein IDs
   - **Upload CSV**: Upload a file with protein IDs
   - Download combined CSV or ZIP with individual files

3. **Data Analysis Mode**:
   - Upload existing CSV files
   - View data overview and statistics
   - Generate visualizations and charts

## 📊 Data Structure

### Main DataFrame Columns

| Column | Description | Type |
|--------|-------------|------|
| `Protein_ID` | PhosphoSitePlus protein ID | Integer |
| `PhosphoSite_Protein_Name` | Official protein name | String |
| `Alt_Name` | Individual alternative name | String |
| `UniProt_ID` | UniProt database ID | String |
| `Gene_Symbols` | Gene symbol | String |
| `Original_Alt_Names` | Complete original alt names string | String |

### Data Explosion Feature

The scraper automatically "explodes" alternative names by splitting them on semicolons:

**Original Data:**
```
Alt_Names: "cdc2-related protein kinase; CDK2; CDKN2; cell devision kinase 2"
```

**Exploded Data:**
```
Row 1: Alt_Name = "cdc2-related protein kinase"
Row 2: Alt_Name = "CDK2"
Row 3: Alt_Name = "CDKN2"
Row 4: Alt_Name = "cell devision kinase 2"
```

### Output Files

- **Individual**: `{protein_name}_details_exploded.csv`
- **Combined**: `all_proteins_details_exploded_{start_id}_{end_id}.csv`
- **ZIP Archives**: Individual protein files in compressed format

## ⚙️ Configuration

### Scraper Configuration
```python
CONFIG = {
    'headless': True,                    # Browser visibility
    'start_protein_id': 1035,           # Starting protein ID
    'end_protein_id': 1035,             # Ending protein ID
    'max_retries': 3,                   # Retry attempts
}
```

### Anti-Detection Settings
- **User Agent**: Realistic browser user agent
- **Viewport**: Random viewport sizes
- **Delays**: Random delays between requests
- **Mouse Movements**: Simulates human-like behavior
- **Cookie Management**: Saves and reuses cookies

## 🔧 Troubleshooting

### Common Issues

#### 1. Playwright Browser Not Found
```bash
playwright install chromium
```

#### 2. Dependencies Not Installed
```bash
pip install -r requirements.txt
```

#### 3. Port Already in Use (Streamlit)
```bash
streamlit run streamlit_protein_app.py --server.port 8502
```

#### 4. Scraping Fails
- Check internet connection
- Verify protein ID exists on PhosphoSitePlus
- Try again after a few minutes (rate limiting)
- Check if website structure has changed

### Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "No protein record found" | Protein ID doesn't exist | Verify protein ID on PhosphoSitePlus |
| "Error scraping protein" | Network issue or blocking | Check connection, try again later |
| "Could not find Protein Information tab" | Website structure changed | Update selectors in scraper |
| "Cloudflare challenge detected" | Anti-bot protection | Wait and retry, or check network |

### Debug Mode
Set `headless: False` in configuration to see browser actions:
```python
CONFIG = {
    'headless': False,  # Shows browser window
}
```

## 📁 File Structure

```
streamlit_protein_name/
├── phosphosite_uniprot.py              # Command-line scraper
├── streamlit_protein_app.py            # Streamlit web app
├── requirements.txt                     # Python dependencies
├── packages.txt                        # System dependencies
├── README.md                          # This file
├── cookies.json                        # Saved cookies (auto-generated)
└── protein_details_data/               # Output directory
    ├── logs/                           # Scraping logs
    └── *.csv                          # Scraped data files
```

### Key Files

- **`phosphosite_uniprot.py`**: Main command-line scraping engine
- **`streamlit_protein_app.py`**: Web interface application
- **`requirements.txt`**: Python package dependencies
- **`cookies.json`**: Browser cookies (auto-generated)

## 🛠️ Technical Details

### Web Scraping Technology
- **Playwright**: Modern browser automation
- **Cloudscraper**: Cloudflare challenge bypass
- **Stealth Techniques**: Anti-detection measures
- **Async/Await**: Non-blocking operations

### Data Processing
- **Pandas**: Data manipulation and analysis
- **Data Explosion**: Automatic splitting of alternative names
- **CSV Export**: Multiple output formats
- **Error Handling**: Robust error recovery

### Web Interface
- **Streamlit**: Interactive web application
- **Plotly**: Data visualizations
- **File Upload**: CSV import capabilities
- **Progress Tracking**: Real-time updates

## 📈 Data Analysis Features

### Visualizations
- **Protein Distribution**: Pie charts showing protein frequency
- **Alt Names Count**: Bar charts of alternative name frequency
- **Gene Symbols Distribution**: Distribution of gene symbols
- **UniProt ID Analysis**: Scatter plots of UniProt references

### Statistics
- **Top Alternative Names**: Most common protein synonyms
- **Gene Symbol Frequency**: Most frequent gene symbols
- **Data Quality Metrics**: Missing data analysis
- **Cross-reference Analysis**: UniProt ID coverage

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Add docstrings to functions
- Include error handling
- Add debug logging

### Testing
- Test with different protein IDs
- Verify data accuracy
- Check error handling
- Test web interface

## 📄 License

This project is for educational and research purposes. Please respect PhosphoSitePlus's terms of service.

## 🙏 Acknowledgments

- **PhosphoSitePlus**: Data source and website
- **Playwright**: Browser automation framework
- **Streamlit**: Web application framework
- **Pandas**: Data manipulation library
- **Plotly**: Data visualization library

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review error messages in the app
3. Verify protein IDs on PhosphoSitePlus
4. Check network connectivity

## 🚀 Quick Start

### Command Line
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run scraper
python phosphosite_uniprot.py
```

### Web App
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Launch web app
streamlit run streamlit_protein_app.py
```

---

**Note**: This tool is designed for research purposes. Please use responsibly and respect the PhosphoSitePlus website's terms of service.
