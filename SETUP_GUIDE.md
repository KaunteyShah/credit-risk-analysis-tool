# Quick Setup Guide for Git Deployment

## Prerequisites
- Python 3.8+
- pip3

## Installation Steps

1. Clone the repository:
```bash
git clone <your-repo-url>
cd Credit_Risk
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Verify data files exist:
```bash
ls data/
# Should show: Sample_data2.csv and SIC_codes.xlsx
```

4. Run the Flask application:
```bash
python3 -m app.flask_main
```

5. Open browser and navigate to:
```
http://127.0.0.1:8001
```

## Expected Output
- Should see: "Loaded 509 companies" and "Loaded 751 SIC codes"
- Web interface should display company data with prediction buttons
- Automatic color coding for accuracy values (Green 80%+, Orange 60-79%, Red <60%)

## Key Features Verified
✅ Relative file paths for cross-platform compatibility
✅ Clean imports without duplications
✅ CORS enabled for frontend functionality
✅ Enhanced SIC matching with dual accuracy
✅ Automatic color coding eliminating backend color logic
✅ Production-ready code structure

## Troubleshooting
- If "python" not found, use "python3"
- If modules missing, ensure requirements.txt is installed
- All paths use relative references from project root