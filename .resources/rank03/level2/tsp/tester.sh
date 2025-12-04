#!/bin/bash
source ../../../main/colors.sh

expected_files="*.c *.h"
rendu_dir="../../../../rendu/tsp"

# Check if rendu directory exists
if [ ! -d "$rendu_dir" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Directory $rendu_dir does not exist$(tput sgr 0)"
    exit 1
fi

# Find C files in rendu directory
c_files=$(find "$rendu_dir" -name "*.c" -type f)
if [ -z "$c_files" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: No .c files found in $rendu_dir$(tput sgr 0)"
    exit 1
fi

# Compile the program
echo "${BLUE}Compiling tsp program...${RESET}"
gcc -Wall -Werror -Wextra -o tsp_test $c_files -lm 2>/dev/null
if [ $? -ne 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Compilation error$(tput sgr 0)"
    exit 1
fi

# Test 1: Example from sub.txt (3x3 grid)
echo "${BLUE}Testing sub.txt 3x3 grid example...${RESET}"
cat > test1_input.txt << 'EOF'
0, 0
1, 0
2, 0
0, 1
1, 1
2, 1
1, 2
2, 2
EOF

./tsp_test < test1_input.txt > output1.txt 2>/dev/null
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Program exited with error code $exit_code$(tput sgr 0)"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Check if output is exactly 8.00 as specified in sub.txt
output=$(cat output1.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

expected="8.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: 3x3 grid result from sub.txt incorrect$(tput sgr 0)"
    echo "Expected: $expected (as specified in sub.txt)"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 2: Example from sub.txt (square.txt)
echo "${BLUE}Testing sub.txt square example...${RESET}"
cat > test2_input.txt << 'EOF'
1, 1
0, 1
1, 0
0, 0
EOF

./tsp_test < test2_input.txt > output2.txt 2>/dev/null
output=$(cat output2.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Square perimeter should be 4.00 as specified in sub.txt
expected="4.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Square result from sub.txt incorrect$(tput sgr 0)"
    echo "Expected: $expected (as specified in sub.txt)"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 3: Single point
echo "${BLUE}Testing single point...${RESET}"
cat > test3_input.txt << 'EOF'
0, 0
EOF

./tsp_test < test3_input.txt > output3.txt 2>/dev/null
output=$(cat output3.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Single point should have distance 0.00
expected="0.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Single point should have distance 0.00$(tput sgr 0)"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 4: Two points
echo "${BLUE}Testing two points...${RESET}"
cat > test4_input.txt << 'EOF'
0, 0
1, 1
EOF

./tsp_test < test4_input.txt > output4.txt 2>/dev/null
output=$(cat output4.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Two points: distance is 2 * sqrt(2) ≈ 2.83
# We'll check if it's approximately correct (within 0.01)
distance=$(echo "$output" | cut -d'.' -f1-2)
expected_float=2.83
actual_float=$(printf "%.2f" "$distance")
if [ "$actual_float" != "2.83" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Two points distance incorrect$(tput sgr 0)"
    echo "Expected approximately: 2.83"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 5: Square (4 points)
echo "${BLUE}Testing square (4 points)...${RESET}"
cat > test5_input.txt << 'EOF'
0, 0
1, 0
1, 1
0, 1
EOF

./tsp_test < test5_input.txt > output5.txt 2>/dev/null
output=$(cat output5.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Square perimeter should be 4.00
expected="4.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Square result incorrect$(tput sgr 0)"
    echo "Expected: $expected"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 6: Floating point coordinates
echo "${BLUE}Testing floating point coordinates...${RESET}"
cat > test6_input.txt << 'EOF'
0.5, 0.5
1.5, 0.5
1.5, 1.5
0.5, 1.5
EOF

./tsp_test < test6_input.txt > output6.txt 2>/dev/null
output=$(cat output6.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# This should also be 4.00 (1x1 square)
expected="4.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Floating point square result incorrect$(tput sgr 0)"
    echo "Expected: $expected"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Test 7: Empty input
echo "${BLUE}Testing empty input...${RESET}"
echo "" | ./tsp_test > output7.txt 2>/dev/null
output=$(cat output7.txt | tr -d '\n')
# Empty input should produce 0.00 or handle gracefully
if [[ "$output" != "0.00" && -n "$output" ]]; then
    # Accept either 0.00 or empty output for empty input
    if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Invalid output format for empty input$(tput sgr 0)"
        echo "Got: '$output'"
        rm -f tsp_test test*_input.txt output*.txt
        exit 1
    fi
fi

# Test 8: Collinear points
echo "${BLUE}Testing collinear points...${RESET}"
cat > test8_input.txt << 'EOF'
0, 0
1, 0
2, 0
3, 0
EOF

./tsp_test < test8_input.txt > output8.txt 2>/dev/null
output=$(cat output8.txt | tr -d '\n')
if [[ ! "$output" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Output format should be X.XX$(tput sgr 0)"
    echo "Got: '$output'"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# For collinear points, optimal path is 0->3->2->1->0 or similar, distance = 6.00
expected="6.00"
if [ "$output" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Collinear points result incorrect$(tput sgr 0)"
    echo "Expected: $expected"
    echo "Got: $output"
    rm -f tsp_test test*_input.txt output*.txt
    exit 1
fi

# Cleanup
rm -f tsp_test test*_input.txt output*.txt

echo "$(tput setaf 2)$(tput bold)PASSED 🎉$(tput sgr 0)"
exit 0
