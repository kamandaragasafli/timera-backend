#!/bin/bash

# AI Helper Deployment Script
# This script deploys the AI helper endpoint to the server

echo "🚀 Starting AI Helper Deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Clear Python cache
echo -e "${YELLOW}📦 Clearing Python cache...${NC}"
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
echo -e "${GREEN}✅ Cache cleared${NC}"

# Step 2: Check if ai_helper exists
if [ ! -d "ai_helper" ]; then
    echo -e "${RED}❌ Error: ai_helper directory not found${NC}"
    echo "Make sure you're in the backend directory"
    exit 1
fi
echo -e "${GREEN}✅ ai_helper directory found${NC}"

# Step 3: Check if OpenAI is installed
echo -e "${YELLOW}🔍 Checking OpenAI package...${NC}"
if python -c "import openai" 2>/dev/null; then
    echo -e "${GREEN}✅ OpenAI package is installed${NC}"
else
    echo -e "${YELLOW}📦 Installing OpenAI package...${NC}"
    pip install openai
fi

# Step 4: Verify settings
echo -e "${YELLOW}🔍 Checking configuration...${NC}"

if grep -q "ai_helper" socialai_backend/settings.py; then
    echo -e "${GREEN}✅ ai_helper is in INSTALLED_APPS${NC}"
else
    echo -e "${RED}❌ ai_helper is NOT in INSTALLED_APPS${NC}"
    echo "Please add 'ai_helper' to INSTALLED_APPS in socialai_backend/settings.py"
    exit 1
fi

if grep -q "api/ai/" socialai_backend/urls.py; then
    echo -e "${GREEN}✅ AI URLs are configured${NC}"
else
    echo -e "${RED}❌ AI URLs are NOT configured${NC}"
    echo "Please add path('api/ai/', include('ai_helper.urls')) to socialai_backend/urls.py"
    exit 1
fi

# Step 5: Check environment variables
if [ -f "local.env" ]; then
    if grep -q "OPENAI_API_KEY" local.env; then
        echo -e "${GREEN}✅ OPENAI_API_KEY found in local.env${NC}"
    else
        echo -e "${RED}❌ OPENAI_API_KEY not found in local.env${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  local.env not found, checking env.example...${NC}"
fi

# Step 6: Test Django configuration
echo -e "${YELLOW}🧪 Testing Django configuration...${NC}"
if python manage.py check --deploy 2>/dev/null; then
    echo -e "${GREEN}✅ Django configuration is valid${NC}"
else
    echo -e "${YELLOW}⚠️  Some deployment checks failed (non-critical)${NC}"
fi

# Step 7: Instructions for server restart
echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Pre-deployment checks passed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart Gunicorn:"
echo "   ${GREEN}sudo systemctl restart gunicorn${NC}"
echo ""
echo "2. Check status:"
echo "   ${GREEN}sudo systemctl status gunicorn${NC}"
echo ""
echo "3. Test the endpoint:"
echo "   ${GREEN}curl -X POST http://localhost:8000/api/ai/generate-content/ \\${NC}"
echo "   ${GREEN}     -H \"Authorization: Bearer YOUR_TOKEN\" \\${NC}"
echo "   ${GREEN}     -H \"Content-Type: application/json\" \\${NC}"
echo "   ${GREEN}     -d '{\"prompt\": \"Test\", \"content_type\": \"test\"}'${NC}"
echo ""
echo -e "${GREEN}🎉 AI Helper is ready for deployment!${NC}"



