#!/bin/bash
source ../../../main/colors.sh

expected_files="*.c *.h"
rendu_dir="../../../../rendu/rip"

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
echo "${BLUE}Compiling rip program...${RESET}"
gcc -Wall -Werror -Wextra -o rip_test $c_files 2>/dev/null
if [ $? -ne 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Compilation error$(tput sgr 0)"
    exit 1
fi

# Function to check if a string has balanced parentheses
check_balanced() {
    local str="$1"
    local count=0
    for (( i=0; i<${#str}; i++ )); do
        char="${str:$i:1}"
        if [ "$char" = "(" ]; then
            count=$((count + 1))
        elif [ "$char" = ")" ]; then
            count=$((count - 1))
            if [ $count -lt 0 ]; then
                return 1  # Unbalanced
            fi
        fi
    done
    [ $count -eq 0 ]
}

# Function to count non-space characters
count_non_space() {
    local str="$1"
    echo -n "$str" | tr -d ' ' | wc -c | tr -d ' '
}

# Test 1: Example from subject - rip '(()'
echo "${BLUE}Testing example: rip '(()'...${RESET}"
./rip_test '(()' > output1.txt 2>/dev/null
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Program exited with error code $exit_code$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Check if solutions are valid
lines=$(wc -l < output1.txt)
if [ $lines -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should produce at least one solution$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

valid_solutions=0
while IFS= read -r line; do
    if check_balanced "$line"; then
        valid_solutions=$((valid_solutions + 1))
        # Check if solution uses only original characters or spaces
        cleaned=$(echo "$line" | tr -d ' ()')
        if [ -n "$cleaned" ]; then
            echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' contains invalid characters$(tput sgr 0)"
            rm -f rip_test output*.txt
            exit 1
        fi
    else
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' is not balanced$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
done < output1.txt

if [ $valid_solutions -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: No balanced solutions found$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Test 2: Already balanced string
echo "${BLUE}Testing already balanced: rip '((()()())())'...${RESET}"
./rip_test '((()()())())' > output2.txt 2>/dev/null
expected="((()()())())"
if [ "$(cat output2.txt)" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Already balanced string should return itself$(tput sgr 0)"
    echo "Expected: '$expected'"
    echo "Got: '$(cat output2.txt)'"
    rm -f rip_test output*.txt
    exit 1
fi

# Test 3: Example '()())()' 
echo "${BLUE}Testing example: rip '()())()' ...${RESET}"
./rip_test '()())()' > output3.txt 2>/dev/null
lines=$(wc -l < output3.txt)
if [ $lines -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should produce at least one solution$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Check all solutions are balanced
while IFS= read -r line; do
    if ! check_balanced "$line"; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' is not balanced$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
    # Check that we only removed characters (no additions)
    original_count=$(echo '()())()' | wc -c)
    solution_count=$(echo "$line" | wc -c)
    if [ $solution_count -ne $original_count ]; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution length doesn't match original$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
done < output3.txt

# Test 4: Simple unbalanced case ')('
echo "${BLUE}Testing simple case: rip ')(' ...${RESET}"
./rip_test ')(' > output4.txt 2>/dev/null
lines=$(wc -l < output4.txt)
if [ $lines -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should produce at least one solution (empty string)$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Should produce "  " (two spaces) as one solution
found_empty=0
while IFS= read -r line; do
    if ! check_balanced "$line"; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' is not balanced$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
    # Check if this is effectively empty (all spaces)
    non_space_count=$(count_non_space "$line")
    if [ $non_space_count -eq 0 ]; then
        found_empty=1
    fi
done < output4.txt

if [ $found_empty -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should find empty solution for ')('$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Test 5: Empty string
echo "${BLUE}Testing empty string...${RESET}"
./rip_test '' > output5.txt 2>/dev/null
expected=""
if [ "$(cat output5.txt)" != "$expected" ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Empty string should return empty$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# Test 6: Only opening parentheses '((('
echo "${BLUE}Testing only opening: rip '(((' ...${RESET}"
./rip_test '(((' > output6.txt 2>/dev/null
lines=$(wc -l < output6.txt)
if [ $lines -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should produce at least one solution$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# All solutions should be balanced
while IFS= read -r line; do
    if ! check_balanced "$line"; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' is not balanced$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
done < output6.txt

# Test 7: Only closing parentheses ')))'
echo "${BLUE}Testing only closing: rip ')))' ...${RESET}"
./rip_test ')))' > output7.txt 2>/dev/null
lines=$(wc -l < output7.txt)
if [ $lines -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should produce at least one solution$(tput sgr 0)"
    rm -f rip_test output*.txt
    exit 1
fi

# All solutions should be balanced
while IFS= read -r line; do
    if ! check_balanced "$line"; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' is not balanced$(tput sgr 0)"
        rm -f rip_test output*.txt
        exit 1
    fi
done < output7.txt

# Test 8: Wrong number of arguments
echo "${BLUE}Testing wrong number of arguments...${RESET}"
./rip_test > temp.txt 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should fail with no arguments$(tput sgr 0)"
    rm -f rip_test output*.txt temp.txt
    exit 1
fi

./rip_test '()' '()' > temp.txt 2>&1
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "$(tput setaf 1)$(tput bold)FAIL: Should fail with too many arguments$(tput sgr 0)"
    rm -f rip_test output*.txt temp.txt
    exit 1
fi

# Test 9: Check minimum removals property
echo "${BLUE}Testing minimum removals property...${RESET}"
./rip_test '((())' > output9.txt 2>/dev/null
# For '((())', we need to remove exactly 1 character to balance
# All solutions should have exactly 4 non-space characters
while IFS= read -r line; do
    non_space_count=$(count_non_space "$line")
    if [ $non_space_count -ne 4 ]; then
        echo "$(tput setaf 1)$(tput bold)FAIL: Solution '$line' doesn't have minimum removals$(tput sgr 0)"
        echo "Expected 4 non-space chars, got $non_space_count"
        rm -f rip_test output*.txt temp.txt
        exit 1
    fi
done < output9.txt

# Cleanup
rm -f rip_test output*.txt temp.txt

echo "$(tput setaf 2)$(tput bold)PASSED 🎉$(tput sgr 0)"
exit 0