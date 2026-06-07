
#!/bin/bash
source ../../../main/colors.sh
file1=flood_fill.c
file2=../../../../rendu/flood_fill/flood_fill.c

# Compile reference and student code
gcc -Wall -Wextra -Werror -o ref.out "$file1" main.c 
gcc -Wall -Wextra -Werror -o user.out "$file2" main.c 

# Test cases
test_case() {
    input=$1
    # Here we're redirecting the output into a file to compare results
    ./ref.out > ref.txt 2>/dev/null
    ./user.out > user.txt 2>/dev/null

    if ! diff -q ref.txt user.txt >/dev/null; then
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$(cat ref.txt)\""
        echo "${RED}Your Output:${RESET}     \"$(cat user.txt)\""
        rm -f ref.out user.out ref.txt user.txt 2>/dev/null
        exit 1
    fi
}

# Example test cases (replace with your actual input data if necessary)
test_case "Map 1\nStart (7, 4)\nStart (3, 1)\nMap 2\nStart (0, 0)\n" 

# Cleanup
rm -f ref.out user.out ref.txt user.txt
echo "$(tput setaf 2)$(tput bold)PASSED 🎉$(tput sgr 0)"
exit 0

