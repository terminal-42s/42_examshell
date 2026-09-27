#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

clear

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                   🔄 UPDATING 42 EXAM SHELL               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Check if git is available
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Error: Git is not installed${NC}"
    exit 1
fi

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Show current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}📍 Current branch: ${YELLOW}$CURRENT_BRANCH${NC}"
echo ""

# Fetch latest changes
echo -e "${BLUE}📥 Fetching latest changes from repository...${NC}"
if ! git fetch origin; then
    echo -e "${RED}❌ Failed to fetch${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Fetch successful${NC}"
echo ""

# Check if there are updates available
BEHIND=$(git rev-list --count HEAD..origin/$CURRENT_BRANCH 2>/dev/null)

if [ "$BEHIND" -eq 0 ]; then
    echo -e "${GREEN}✅ You are up to date!${NC}"
    echo ""
else
    echo -e "${YELLOW}📦 $BEHIND update(s) available${NC}"
    echo ""
    
    # Show what will be updated
    echo -e "${BLUE}📋 Changes to be pulled:${NC}"
    git log HEAD..origin/$CURRENT_BRANCH --oneline | sed 's/^/   /'
    echo ""
    
    # Pull latest changes
    echo -e "${BLUE}⬇️  Pulling latest changes...${NC}"
    if ! git pull origin $CURRENT_BRANCH; then
        echo -e "${RED}❌ Failed to pull${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Pull successful${NC}"
    echo ""
fi

# Update file permissions for tester scripts
echo -e "${BLUE}🔐 Updating file permissions...${NC}"
find .resources -name "tester.sh" -exec chmod +x {} \; 2>/dev/null
echo -e "${GREEN}✅ Permissions updated${NC}"
echo ""

# Show final status
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}${BOLD}✨ Update Complete!${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo -e "${CYAN}Ready to continue? Press enter to return to menu.${NC}"
read -r

cd .resources/main
bash menu.sh
