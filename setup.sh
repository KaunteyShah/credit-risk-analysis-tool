#!/bin/bash

# Credit Risk Multi-Agent System Setup Script
echo "🚀 Setting up Credit Risk Multi-Agent Anomaly Detection System"
echo "=============================================================="

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set up environment variables template
echo "🔧 Creating environment variables template..."
cat > .env.template << EOF
# Companies House API
COMPANIES_HOUSE_API_KEY=your_companies_house_api_key_here

# OpenAI API (for AI suggestions)
OPENAI_API_KEY=your_openai_api_key_here

# Databricks Configuration
DATABRICKS_HOST=your_databricks_host_here
DATABRICKS_TOKEN=your_databricks_token_here
DATABRICKS_CLUSTER_ID=your_cluster_id_here

# Optional: External API Keys
DUEDIL_API_KEY=your_duedil_api_key_here
CREDITSAFE_USERNAME=your_creditsafe_username_here
CREDITSAFE_PASSWORD=your_creditsafe_password_here
EOF

echo "⚙️  Environment template created at .env.template"
echo "   Please copy to .env and fill in your actual API keys"

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/raw data/processed data/exports

# Create logs directory
mkdir -p logs

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🔄 Next steps:"
echo "1. Copy .env.template to .env and configure your API keys"
echo "2. Upload the project to your Databricks workspace"
echo "3. Run the demo: python demo.py"
echo "4. Open the Jupyter notebook in Databricks for full functionality"
echo ""
echo "📚 Key files:"
echo "   • README.md - Project documentation"
echo "   • demo.py - Local demonstration script"
echo "   • notebooks/Credit_Risk_Multi_Agent_Demo.ipynb - Databricks notebook"
echo "   • src/agents/ - Individual agent implementations"
echo "   • config/api_config.yaml - Configuration settings"
echo ""
echo "🎯 For production deployment:"
echo "   • Store API keys in Databricks secrets"
echo "   • Set up Delta Lake for data storage"
echo "   • Configure MLflow for model tracking"
echo "   • Implement real-time monitoring"
