#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Cleanup
cleanup() {
    rm -rf ref_life user_life \
        ref_*.txt user_*.txt \
        
        if [ -n "$TMP_USER" ]; then
            rm -rf "$TMP_USER"
        fi
}

trap cleanup EXIT INT TERM

# User solution path
USER_DIR="../../../../rendu/life"

# Check user directory
if [ ! -d "$USER_DIR" ]; then
    echo -e "${RED}❌ User directory not found: $USER_DIR${NC}"
    exit 1
fi

# Create temporary folder
TMP_USER=$(mktemp -d)
cp "$USER_DIR"/*.c "$TMP_USER/" 2>/dev/null
cp "$USER_DIR"/*.h "$TMP_USER/" 2>/dev/null

USER_C_FILES=$(find "$TMP_USER" -name "*.c")
USER_H_FILES=$(find "$TMP_USER" -name "*.h")

if [ -z "$USER_C_FILES" ] || [ -z "$USER_H_FILES" ]; then
    echo -e "${RED}❌ User solution not found: No .c or .h files${NC}"
    exit 1
fi

# Compile reference
echo -e "${BLUE}📦 Compiling reference solution...${NC}"
gcc -Wall -Wextra -Werror -std=c99 -o ref_life life.c

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Reference compilation failed!${NC}"
    exit 1
fi

# Compile user
echo -e "${BLUE}📦 Compiling user solution...${NC}"
gcc -Wall -Wextra -Werror -std=c99 \
    $USER_C_FILES \
    -I"$TMP_USER" \
    -o user_life

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ User compilation failed!${NC}"
    exit 1
fi

# Helper function to run tests silently
run_test() {
    local test_name="$1"
    local input="$2"
    local rows="$3"
    local cols="$4"
    local iter="$5"
    local ref_out="ref_${test_name}.txt"
    local user_out="user_${test_name}.txt"

    echo "$input" | ./ref_life "$rows" "$cols" "$iter" > "$ref_out" 2>&1
    #Run user test with timeout to prevent infinite loop
    echo "$input" | timeout 2 ./user_life "$rows" "$cols" "$iter" > "$user_out" 2>&1
    status=$?
    
    if [ $status -eq 124 ]; then
        echo -e "${RED}❌ User program timed out (possible infinite loop)${NC}"
        exit 1
    elif [ $status -ne 0 ]; then
        echo -e "${RED}❌ User program crashed (exit code $status)${NC}"
        exit 1
    fi

    if diff -q "$ref_out" "$user_out" >/dev/null; then
        return 0
    else
        echo -e "${RED}❌ $test_name failed! Output differs from reference:${NC}"
        diff "$ref_out" "$user_out"
        return 1
    fi
}

# Run all tests
run_test "Test1_Basic" "sdxddssaaww" 5 5 0
test1_match=$?

run_test "Test2_Complex" "sdxssdswdxddddsxaadwxwdxwaa" 10 6 0
test2_match=$?

run_test "Test3_Vertical" "dxss" 3 3 0
test3_match=$?

run_test "Test4_Evolution1" "dxss" 3 3 1
test4_match=$?

run_test "Test5_Evolution2" "dxss" 3 3 2
test5_match=$?

run_test "Test6_Empty" "" 3 3 0
test6_match=$?

# Valgrind check silently
valgrind_output=$(echo 'sdxddssaaww' | valgrind \
    --leak-check=full --show-leak-kinds=all --track-origins=yes -s \
    ./user_life 5 5 0 2>&1)
has_leaks=$(echo "$valgrind_output" | grep -E "definitely lost: [^0]" || echo "")
has_errors=$(echo "$valgrind_output" | grep -E "ERROR SUMMARY: [^0]" || echo "")

# Determine overall result
all_passed=true
for t in $test1_match $test2_match $test3_match $test4_match $test5_match $test6_match; do
    if [ $t -ne 0 ]; then
        all_passed=false
    fi
done
if [ -n "$has_leaks" ] || [ -n "$has_errors" ]; then
    all_passed=false
fi

# Print errors only if something failed
if [ "$all_passed" = true ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
else
    echo "======================================="
    echo -e "${YELLOW}Detailed Issues:${NC}"

    [ $test1_match -ne 0 ] && echo -e "${RED}→ Test1_Basic failed${NC}"
    [ $test2_match -ne 0 ] && echo -e "${RED}→ Test2_Complex failed${NC}"
    [ $test3_match -ne 0 ] && echo -e "${RED}→ Test3_Vertical failed${NC}"
    [ $test4_match -ne 0 ] && echo -e "${RED}→ Test4_Evolution1 failed${NC}"
    [ $test5_match -ne 0 ] && echo -e "${RED}→ Test5_Evolution2 failed${NC}"
    [ $test6_match -ne 0 ] && echo -e "${RED}→ Test6_Empty failed${NC}"

    [ -n "$has_leaks" ] && echo -e "${RED}→ Memory leaks detected${NC}"
    [ -n "$has_errors" ] && echo -e "${RED}→ Valgrind errors detected${NC}"
    echo "======================================="
fi
