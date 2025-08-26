#!/bin/bash

echo "🚀 Inventory Dashboard Deployment Script"
echo "========================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Check if remote origin exists
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "❌ No remote origin found. Please add your GitHub repository:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    exit 1
fi

echo "✅ Git repository configured"

# Check if all required files exist
required_files=("app.py" "requirements.txt" "render.yaml" ".streamlit/config.toml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

echo "✅ All required files present"

# Check if creds.json exists (for local testing)
if [ -f "creds.json" ]; then
    echo "⚠️  Warning: creds.json found. Make sure it's in .gitignore"
else
    echo "ℹ️  No creds.json found (expected for deployment)"
fi

echo ""
echo "📋 Deployment Checklist:"
echo "1. ✅ Repository structure ready"
echo "2. 🔄 Push to GitHub: git push origin main"
echo "3. 🌐 Go to render.com and create new Web Service"
echo "4. 🔗 Connect your GitHub repository"
echo "5. 🔑 Add environment variable GOOGLE_CREDENTIALS_JSON"
echo "6. 🚀 Deploy!"

echo ""
echo "📝 Next steps:"
echo "   git add ."
echo "   git commit -m 'Prepare for Render deployment'"
echo "   git push origin main"
echo ""
echo "Then visit: https://render.com"
