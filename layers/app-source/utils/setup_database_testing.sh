#!/bin/bash
# setup_database_testing.sh - Setup script for database layer testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up Database Layer Testing Environment${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if we're in the right directory
if [[ ! -f "DatabaseManager.py" ]]; then
    echo -e "${RED}❌ Please run this script from the layers/app-source/utils directory${NC}"
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo -e "${BLUE}🐍 Python version: ${python_version}${NC}"

# Install required dependencies
echo -e "\n${YELLOW}📦 Installing required dependencies...${NC}"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 not found. Please install pip3 first.${NC}"
    exit 1
fi

# Install psycopg2-binary
echo -e "Installing psycopg2-binary..."
pip3 install psycopg2-binary --quiet

# Install boto3 for S3 integration (optional)
echo -e "Installing boto3..."
pip3 install boto3 --quiet

echo -e "${GREEN}✅ Dependencies installed successfully${NC}"

# Check DATABASE_URL
echo -e "\n${YELLOW}🔗 Checking database configuration...${NC}"

if [[ -z "$DATABASE_URL" ]]; then
    echo -e "${YELLOW}⚠️  DATABASE_URL environment variable not set${NC}"
    echo -e "${BLUE}Please set it with one of these formats:${NC}"
    echo -e "  Local PostgreSQL:"
    echo -e "    export DATABASE_URL='postgresql://username:password@localhost:5432/database_name'"
    echo -e "  AWS RDS:"
    echo -e "    export DATABASE_URL='postgresql://username:password@your-rds-endpoint.amazonaws.com:5432/database_name'"
    echo -e ""
    echo -e "${BLUE}Example for local testing:${NC}"
    echo -e "    export DATABASE_URL='postgresql://postgres:password@localhost:5432/climate_risk_rag'"
    echo -e ""
    read -p "Do you want to set DATABASE_URL now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your DATABASE_URL: " db_url
        export DATABASE_URL="$db_url"
        echo "export DATABASE_URL='$db_url'" >> ~/.bashrc
        echo -e "${GREEN}✅ DATABASE_URL set and saved to ~/.bashrc${NC}"
    else
        echo -e "${YELLOW}⚠️  You'll need to set DATABASE_URL before running tests${NC}"
    fi
else
    # Mask password in display
    masked_url=$(echo "$DATABASE_URL" | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/')
    echo -e "${GREEN}✅ DATABASE_URL configured: ${masked_url}${NC}"
fi

# Test database connection
if [[ -n "$DATABASE_URL" ]]; then
    echo -e "\n${YELLOW}🔌 Testing database connection...${NC}"
    
    # Try to connect using psql if available
    if command -v psql &> /dev/null; then
        if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
            echo -e "${GREEN}✅ Database connection successful${NC}"
        else
            echo -e "${RED}❌ Database connection failed${NC}"
            echo -e "${YELLOW}Please check your DATABASE_URL and ensure PostgreSQL is running${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  psql not found, skipping connection test${NC}"
        echo -e "${BLUE}You can test the connection by running the test scripts${NC}"
    fi
fi

# Check if schema needs to be applied
echo -e "\n${YELLOW}📋 Database schema setup...${NC}"

if [[ -f "schema/postgresql_schema.sql" ]]; then
    echo -e "${GREEN}✅ PostgreSQL schema file found${NC}"
    
    if [[ -n "$DATABASE_URL" ]] && command -v psql &> /dev/null; then
        read -p "Do you want to apply the database schema now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}Applying database schema...${NC}"
            if psql "$DATABASE_URL" -f schema/postgresql_schema.sql; then
                echo -e "${GREEN}✅ Database schema applied successfully${NC}"
            else
                echo -e "${RED}❌ Failed to apply database schema${NC}"
                echo -e "${YELLOW}You may need to apply it manually${NC}"
            fi
        fi
    else
        echo -e "${BLUE}To apply the schema manually, run:${NC}"
        echo -e "  psql \$DATABASE_URL -f schema/postgresql_schema.sql"
    fi
else
    echo -e "${RED}❌ PostgreSQL schema file not found${NC}"
fi

# Show available test scripts
echo -e "\n${YELLOW}🧪 Available test scripts:${NC}"
echo -e "${BLUE}1. Comprehensive test suite:${NC}"
echo -e "   python3 test_database_layer.py"
echo -e ""
echo -e "${BLUE}2. Manual/interactive testing:${NC}"
echo -e "   python3 manual_test.py"
echo -e ""
echo -e "${BLUE}3. Quick connection test:${NC}"
echo -e "   python3 -c \"from DatabaseManager import DatabaseManager; print('✅ Import successful'); db = DatabaseManager(); print('✅ Connection successful')\""

# Offer to run tests
echo -e "\n${YELLOW}🚀 Ready to run tests!${NC}"
read -p "Do you want to run the comprehensive test suite now? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Running comprehensive test suite...${NC}"
    echo -e "${BLUE}=================================${NC}"
    python3 test_database_layer.py
else
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo -e "${BLUE}You can now run tests manually:${NC}"
    echo -e "  python3 test_database_layer.py"
    echo -e "  python3 manual_test.py"
fi

echo -e "\n${GREEN}🎉 Database testing environment setup complete!${NC}"
