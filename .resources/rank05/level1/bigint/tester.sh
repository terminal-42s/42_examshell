#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Comprehensive Test Script for bigint
echo -e "${BLUE}🔍 Running COMPREHENSIVE TESTING for bigint${NC}"
echo "=========================================="
echo ""

# Compile the reference solution
echo -e "${BLUE}📦 Compiling reference solution...${NC}"
g++ -Wall -Wextra -Werror -std=c++98 -o ref_bigint main.cpp bigint.cpp

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Reference compilation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Reference compilation successful!${NC}"
echo ""

# Check if user solution exists
USER_HPP="../../../../rendu/bigint/bigint.hpp"
USER_CPP="../../../../rendu/bigint/bigint.cpp"
if [ ! -f "$USER_HPP" ] || [ ! -f "$USER_CPP" ]; then
    echo -e "${RED}❌ User solution not found: $USER_HPP or $USER_CPP${NC}"
    exit 1
fi

# Copy and compile user solution
echo -e "${BLUE}📦 Compiling user solution...${NC}"
cp main.cpp user_main.cpp
cp "$USER_HPP" user_bigint.hpp
cp "$USER_CPP" user_bigint.cpp
sed 's/#include "bigint.hpp"/#include "user_bigint.hpp"/' user_main.cpp > user_main.tmp.cpp
mv user_main.tmp.cpp user_main.cpp
g++ -Wall -Wextra -Werror -std=c++98 -o user_bigint user_main.cpp user_bigint.cpp
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ User compilation failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ User compilation successful!${NC}"
echo ""

# Run both and capture output
echo -e "${BLUE}🚀 Running tests...${NC}"
./ref_bigint > ref_output.txt 2>&1
echo "[DEBUG] Reference output:"; cat ref_output.txt
./user_bigint > user_output.txt 2>&1
echo "[DEBUG] User output:"; cat user_output.txt

# Compare outputs
output_match=true
output_error_msg=""
if diff -q ref_output.txt user_output.txt > /dev/null; then
    echo -e "${GREEN}✅ Output matches reference!${NC}"
else
    echo -e "${RED}❌ Output does NOT match reference!${NC}"
    echo -e "${YELLOW}--- Reference Output ---${NC}"
    cat ref_output.txt
    echo -e "${YELLOW}--- Your Output ---${NC}"
    cat user_output.txt
    echo -e "${YELLOW}--- Diff ---${NC}"
    diff ref_output.txt user_output.txt
    output_match=false
    output_error_msg="Output does not match reference solution."
fi

# Run with valgrind for memory leak checking
echo -e "${BLUE}🚀 Executing valgrind analysis...${NC}"
echo "Command: valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes -s ./user_bigint"
echo ""

# Capture valgrind output to analyze
valgrind_output=$(valgrind \
    --leak-check=full \
    --show-leak-kinds=all \
    --track-origins=yes \
    -s \
    --error-exitcode=1 \
    ./user_bigint 2>&1)

exit_code=$?

# Display the full output
echo "$valgrind_output"

echo ""
echo -e "${BLUE}🏁 Valgrind analysis completed with exit code: $exit_code${NC}"
echo ""

# Parse and analyze the output
echo "======================================="
echo -e "${YELLOW}📊 DETAILED ANALYSIS RESULTS:${NC}"
echo "======================================="

# Check for memory leaks
has_leaks=false
if echo "$valgrind_output" | grep -q "definitely lost:" && echo "$valgrind_output" | grep "definitely lost:" | grep -v "0 bytes"; then
    has_leaks=true
fi
if echo "$valgrind_output" | grep -q "indirectly lost:" && echo "$valgrind_output" | grep "indirectly lost:" | grep -v "0 bytes"; then
    has_leaks=true
fi
if echo "$valgrind_output" | grep -q "possibly lost:" && echo "$valgrind_output" | grep "possibly lost:" | grep -v "0 bytes"; then
    has_leaks=true
fi

# Check for errors
has_errors=false
if echo "$valgrind_output" | grep -q "ERROR SUMMARY" && echo "$valgrind_output" | grep "ERROR SUMMARY" | grep -v "0 errors"; then
    has_errors=true
fi

# Display results with color coding
echo -n "Memory Leaks: "
if [ "$has_leaks" = true ]; then
    echo -e "${RED}DETECTED - You have memory leaks!${NC}"
else
    echo -e "${GREEN}PASSED - No memory leaks detected${NC}"
fi

echo -n "Valgrind Errors: "
if [ "$has_errors" = true ]; then
    echo -e "${RED}DETECTED - Valgrind found errors!${NC}"
else
    echo -e "${GREEN}PASSED - No valgrind errors${NC}"
fi

echo ""
echo "======================================="
echo -n "OVERALL RESULT: "
if [ "$has_leaks" = false ] && [ "$has_errors" = false ] && [ "$output_match" = true ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}Your bigint implementation is clean!${NC}"
else
    echo -e "${RED}❌ ISSUES DETECTED!${NC}"
    echo -e "${YELLOW}Summary of errors:${NC}"
    if [ "$has_leaks" = true ]; then
        echo -e "${RED}  → Memory leaks detected.${NC}"
    fi
    if [ "$has_errors" = true ]; then
        echo -e "${RED}  → Valgrind errors detected.${NC}"
    fi
    if [ "$output_match" = false ]; then
        echo -e "${RED}  → Output does not match reference solution.${NC}"
    fi
fi
echo "======================================="

# Wait for user to press enter before continuing
read -rp "Press enter to continue..." dummy

# Cleanup temporary files
rm -f ref_bigint user_bigint user_main.cpp user_bigint.hpp user_bigint.cpp ref_output.txt user_output.txt