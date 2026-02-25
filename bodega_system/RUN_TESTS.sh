#!/bin/bash
# RUN_TESTS.sh - Quick script to run tests with common options

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Ukaro Bodegas - Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found!${NC}"
    echo -e "${YELLOW}Installing testing dependencies...${NC}"
    cd ..
    pip install -r requirements.txt
    cd bodega_system
fi

# Parse command line arguments
MODE=${1:-"all"}

case $MODE in
    "quick")
        echo -e "${GREEN}🚀 Running quick tests (no coverage)...${NC}"
        pytest -v
        ;;
    "critical")
        echo -e "${GREEN}🔥 Running CRITICAL tests only...${NC}"
        pytest -v -m critical
        ;;
    "coverage")
        echo -e "${GREEN}📊 Running tests with coverage report...${NC}"
        pytest --cov=. --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${BLUE}Coverage report generated at: htmlcov/index.html${NC}"
        ;;
    "watch")
        echo -e "${GREEN}👀 Running tests in watch mode...${NC}"
        if ! command -v pytest-watch &> /dev/null; then
            echo -e "${YELLOW}Installing pytest-watch...${NC}"
            pip install pytest-watch
        fi
        ptw -- -v
        ;;
    "parallel")
        echo -e "${GREEN}⚡ Running tests in parallel...${NC}"
        if ! command -v pytest &> /dev/null || ! python -c "import xdist" 2> /dev/null; then
            echo -e "${YELLOW}Installing pytest-xdist...${NC}"
            pip install pytest-xdist
        fi
        pytest -v -n auto
        ;;
    "utils")
        echo -e "${GREEN}🔧 Running utils tests only...${NC}"
        pytest -v utils/tests.py
        ;;
    "all")
        echo -e "${GREEN}🎯 Running ALL tests with coverage...${NC}"
        pytest --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}  Test Summary${NC}"
        echo -e "${BLUE}========================================${NC}"
        pytest --cov=. --cov-report=term --cov-report=html
        echo ""
        echo -e "${GREEN}✅ Tests complete!${NC}"
        echo -e "${BLUE}📊 Coverage report: htmlcov/index.html${NC}"
        ;;
    "help")
        echo "Usage: ./RUN_TESTS.sh [mode]"
        echo ""
        echo "Modes:"
        echo "  quick       Run tests without coverage (fast)"
        echo "  critical    Run only critical tests"
        echo "  coverage    Run tests with full coverage report"
        echo "  watch       Run tests in watch mode (re-run on changes)"
        echo "  parallel    Run tests in parallel (faster)"
        echo "  utils       Run only utils tests"
        echo "  all         Run all tests with coverage (default)"
        echo "  help        Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./RUN_TESTS.sh quick"
        echo "  ./RUN_TESTS.sh critical"
        echo "  ./RUN_TESTS.sh coverage"
        ;;
    *)
        echo -e "${RED}❌ Unknown mode: $MODE${NC}"
        echo -e "${YELLOW}Run ./RUN_TESTS.sh help for usage${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Done!${NC}"
echo -e "${BLUE}========================================${NC}"
