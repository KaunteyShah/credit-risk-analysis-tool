# Clean Modular Credit Risk Analysis App

A production-ready Flask application with modern UI and modular architecture for credit risk analysis.

## Features

- 🎨 **Modern UI Design** - Clean, responsive interface with 10% smaller agent icons
- 🏗️ **Modular Architecture** - Component-based backend design
- 📊 **Interactive Workflows** - Visual workflow management and execution
- 🔍 **SIC Code Prediction** - AI-powered industry classification
- 📈 **Dashboard Analytics** - Real-time data visualization
- 🌐 **RESTful API** - Complete API endpoints for all features

## Quick Start

### 1. Install Dependencies

```bash
cd clean_modular_app
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The application will start at `http://localhost:5000`

### 3. Access Features

- **Dashboard**: `http://localhost:5000/` - Main analytics dashboard
- **Workflows**: `http://localhost:5000/workflow` - Interactive workflow designer
- **Health Check**: `http://localhost:5000/health` - System status
- **API Docs**: Available via `/api/*` endpoints

## Project Structure

```
clean_modular_app/
├── app.py                 # Main Flask application
├── workflow_manager.py    # Workflow orchestration
├── requirements.txt       # Dependencies
├── README.md             # This file
├── 
├── app/                  # Core application modules
│   ├── core/            # Dependency injection & services
│   ├── utils/           # Utilities & helpers
│   └── ...
├── 
├── templates/           # HTML templates
│   ├── layouts/        # Base layouts
│   ├── dashboard.html  # Main dashboard
│   └── existing_workflows.html
├── 
├── static/             # CSS, JS, images
│   ├── css/           # Stylesheets (with 10% smaller icons)
│   └── js/            # JavaScript files
└── 
└── data/              # Data files
    ├── SIC_codes.xlsx # Industry codes
    └── Sample_data2.csv
```

## API Endpoints

### Company Data
- `GET /api/companies` - List all companies (with filters)
- `GET /api/companies/<id>` - Get specific company

### SIC Prediction
- `POST /api/predict-sic` - Predict SIC code for company

### Workflows
- `GET /api/modular/workflows` - List available workflows
- `GET /api/modular/workflows/<id>/agents` - Get workflow agents
- `POST /api/modular/workflows/<id>/agents/<agent>/execute` - Execute agent

## Deployment Options

### Option 1: Local Development
```bash
python app.py
```

### Option 2: Production with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3: Docker (create Dockerfile)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Option 4: Azure App Service
1. Push to GitHub repository
2. Create Azure App Service
3. Connect to GitHub for continuous deployment
4. Set startup command: `python app.py`

### Option 5: AWS/Railway/Heroku
- Set environment variable: `PORT=5000`
- Use `app:app` as the WSGI entry point

## Environment Configuration

### Environment Variables
```bash
# Optional configuration
DEBUG=False                    # Enable debug mode
PORT=5000                     # Server port
DATABASE_TYPE=files           # Data source type
```

### Production Considerations
- Set `DEBUG=False` in production
- Use proper WSGI server (gunicorn, uwsgi)
- Configure environment variables
- Set up proper logging
- Use HTTPS in production

## Features Overview

### Dashboard
- Interactive company data table
- Real-time filtering and search
- Visual analytics and charts
- Responsive design for all devices

### Workflows
- Visual workflow designer
- Drag-and-drop agent management
- Real-time execution monitoring
- Modular agent architecture

### Agent Orchestration
- SIC code prediction workflow
- Revenue update processes
- Custom workflow creation
- Agent status monitoring

## Development

### Adding New Features
1. Create new routes in `app.py`
2. Add templates in `templates/`
3. Update CSS/JS in `static/`
4. Update API documentation

### Customizing UI
- Modify CSS in `static/css/modular_style.css`
- Update templates in `templates/`
- Add new JavaScript in `static/js/`

## Support

For issues or questions:
1. Check the logs in the console
2. Verify all dependencies are installed
3. Ensure data files are present
4. Check network connectivity for external APIs

## Version

- **Version**: 1.0.0
- **Last Updated**: October 2025
- **Architecture**: Modular Flask
- **UI Framework**: Bootstrap 5 + Custom CSS