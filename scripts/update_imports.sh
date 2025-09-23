#!/bin/bash
# Script to update import paths for production structure

cd /Users/kaunteyshah/Databricks/Credit_Risk

# Update agent imports
find app/agents/ -name "*.py" -exec sed -i '' 's/from agents\./from app.agents./g' {} \;
find app/agents/ -name "*.py" -exec sed -i '' 's/from utils\./from app.utils./g' {} \;

# Update API imports  
find app/apis/ -name "*.py" -exec sed -i '' 's/from utils\./from app.utils./g' {} \;

# Update core imports
find app/core/ -name "*.py" -exec sed -i '' 's/from src\.apis/from app.apis/g' {} \;
find app/core/ -name "*.py" -exec sed -i '' 's/from src\.agents/from app.agents/g' {} \;

# Update utils imports
find app/utils/ -name "*.py" -exec sed -i '' 's/from agents\./from app.agents./g' {} \;

# Update data layer imports
find app/data_layer/ -name "*.py" -exec sed -i '' 's/from config\./from app.config./g' {} \;

# Update config imports  
find app/config/ -name "*.py" -exec sed -i '' 's/from databricks\.sdk/from databricks.sdk/g' {} \;

echo "Import paths updated successfully!"
