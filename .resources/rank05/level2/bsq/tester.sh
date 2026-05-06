#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


# Cleanup temporary files
cleanup() {
    rm -rf ref_bsq user_bsq \
        ref_output1.txt ref_output2.txt ref_output3.txt ref_output4.txt \
        user_output1.txt user_output2.txt user_output3.txt user_output4.txt \
        test1.map test2.map test3.map \
        
        if [ -n "$TMP_USER" ]; then
            rm -rf "$TMP_USER"
        fi
};

trap cleanup EXIT INT TERM

echo -e "${BLUE}🔍 Running COMPREHENSIVE TESTING for bsq${NC}"
echo "=========================================="
echo ""

# Paths
USER_DIR="../../../../rendu/bsq"

# Check if user solution exists
TMP_USER=$(mktemp -d)

if [ ! -d "$USER_DIR" ]; then
    echo -e "${RED}❌ User rendu folder not found!${NC}"
    exit 1
fi

cp "$USER_DIR"/*.c "$TMP_USER/" 2>/dev/null
cp "$USER_DIR"/*.h "$TMP_USER/" 2>/dev/null

USER_H_FILES=$(find "$TMP_USER" -name "*.h")
USER_C_FILES=$(find "$TMP_USER" -name "*.c")
if [ -z "$USER_C_FILES" ] || [ -z "$USER_H_FILES" ]; then
    echo -e "${RED}❌ User solution not found: No .c or .h files${NC}"
    exit 1
fi

# Compile reference solution
echo -e "${BLUE}📦 Compiling reference solution...${NC}"
gcc -Wall -Wextra -Werror -std=c99 -o ref_bsq main.c bsq.c
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Reference compilation failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Reference compilation successful!${NC}"
echo ""

# Compile user solution
echo -e "${BLUE}📦 Compiling user solution...${NC}"
gcc -Wall -Wextra -Werror -std=gnu99 \
    $USER_C_FILES \
  -I"$TMP_USER" \
  -o user_bsq

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ User compilation failed!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ User compilation successful!${NC}"
echo ""

# Create test maps if missing
cat > test1.map << 'EOF'
9 . o x
...........................
....o......................
............o..............
...........................
....o......................
...............o...........
...........................
......o..............o.....
..o.......o................
EOF

cat > test2.map << 'EOF'
5 . # O
.....
.....
.....
.....
.....
EOF

cat > test3.map << 'EOF'
3 a b c
aaa
aaa
aaa
EOF

# Function to run tests
run_test() {
    local num=$1
    local file=$2
    echo -e "${BLUE}🚀 Running Test $num...${NC}"
    ./ref_bsq "$file" > "ref_output${num}.txt" 2>&1
    timeout 2 ./user_bsq "$file" > "user_output${num}.txt" 2>&1
    status=$?
    if [ $status -eq 124 ]; then
        echo -e "${RED}❌ User program timed out (possible infinite loop)${NC}"
        exit 1
    elif [ $status -ne 0 ]; then
        echo -e "${RED}❌ User program crashed (exit code $status)${NC}"
        exit 1
    fi

    if diff -q "ref_output${num}.txt" "user_output${num}.txt" > /dev/null; then
        echo -e "${GREEN}✅ Test $num output matches reference!${NC}"
        return 0
    else
        echo -e "${RED}❌ Test $num output does NOT match reference!${NC}"
        echo -e "${YELLOW}--- Diff ---${NC}"
        diff "ref_output${num}.txt" "user_output${num}.txt"
        return 1
    fi
}

# Run all tests
tests_passed=true
for i in 1 2 3; do
    run_test "$i" "test${i}.map" || tests_passed=false
done

# Standard input test
echo -e "${BLUE}🚀 Running Test 4 (stdin)...${NC}"
./ref_bsq < test1.map > ref_output4.txt 2>&1
./user_bsq < test1.map > user_output4.txt 2>&1
if diff -q ref_output4.txt user_output4.txt > /dev/null; then
    echo -e "${GREEN}✅ Test 4 output matches reference!${NC}"
else
    echo -e "${RED}❌ Test 4 output does NOT match reference!${NC}"
    diff ref_output4.txt user_output4.txt
    tests_passed=false
fi

# Valgrind check
echo -e "${BLUE}🚀 Running Valgrind memory check...${NC}"
valgrind_output=$(valgrind --leak-check=full --show-leak-kinds=all -s ./user_bsq test1.map 2>&1)
valgrind_exit=$?

echo "$valgrind_output"

if echo "$valgrind_output" | grep -q "definitely lost:" && ! echo "$valgrind_output" | grep -q "definitely lost: 0 bytes"; then
    echo -e "${RED}❌ Memory leaks detected!${NC}"
    tests_passed=false
else
    echo -e "${GREEN}✅ No memory leaks detected.${NC}"
fi

# Summary
echo "======================================="
if [ "$tests_passed" = true ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
else
    echo -e "${RED}❌ SOME TESTS FAILED!${NC}"
fi
echo "======================================="