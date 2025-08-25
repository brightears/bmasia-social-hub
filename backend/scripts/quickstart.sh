#!/bin/bash

# BMA Social Backend Quick Start Script

echo "=================================================="
echo "BMA Social Backend - Quick Start"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Please run this script from the backend directory${NC}"
    exit 1
fi

# Step 1: Check Python version
echo -e "\n${YELLOW}Step 1: Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )\d+\.\d+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo -e "${GREEN}✅ Python $python_version is installed${NC}"
else
    echo -e "${RED}❌ Python 3.11+ is required (found $python_version)${NC}"
    exit 1
fi

# Step 2: Create virtual environment
echo -e "\n${YELLOW}Step 2: Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Step 3: Install dependencies
echo -e "\n${YELLOW}Step 3: Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 4: Check for .env file
echo -e "\n${YELLOW}Step 4: Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please fill in the API keys in the .env file:"
    echo "  - Soundtrack Your Brand credentials"
    echo "  - WhatsApp Business API tokens"
    echo "  - Line Business API tokens"
    echo "  - Google Gemini API key"
    exit 1
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi

# Step 5: Check PostgreSQL
echo -e "\n${YELLOW}Step 5: Checking PostgreSQL...${NC}"
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is installed${NC}"
    
    # Try to connect to database
    if psql -U postgres -lqt | cut -d \| -f 1 | grep -qw bma_social; then
        echo -e "${GREEN}✅ Database 'bma_social' exists${NC}"
    else
        echo -e "${YELLOW}Database 'bma_social' not found. Creating...${NC}"
        createdb bma_social 2>/dev/null || echo -e "${YELLOW}Could not create database (may need sudo)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  PostgreSQL not found - using DATABASE_URL from .env${NC}"
fi

# Step 6: Check Redis
echo -e "\n${YELLOW}Step 6: Checking Redis...${NC}"
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Redis is installed but not running${NC}"
        echo "Start Redis with: redis-server"
    fi
else
    echo -e "${YELLOW}⚠️  Redis not found - using REDIS_URL from .env${NC}"
fi

# Step 7: Run migrations
echo -e "\n${YELLOW}Step 7: Running database migrations...${NC}"
alembic upgrade head 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Could not run migrations - database may not be accessible${NC}"
fi

# Step 8: Seed data (optional)
echo -e "\n${YELLOW}Step 8: Seed data${NC}"
read -p "Do you want to load sample data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/seed_data.py
fi

# Step 9: Start the server
echo -e "\n${GREEN}=================================================="
echo "Setup complete! 🎉"
echo "=================================================="
echo -e "${NC}"
echo "To start the server, run:"
echo "  uvicorn app.main:app --reload --port 8000"
echo ""
echo "API Documentation will be available at:"
echo "  http://localhost:8000/docs"
echo ""
echo "Health check endpoint:"
echo "  http://localhost:8000/health"
echo ""
echo "For production deployment on Render:"
echo "  1. Push code to GitHub"
echo "  2. Connect repository to Render"
echo "  3. Deploy using render.yaml configuration"