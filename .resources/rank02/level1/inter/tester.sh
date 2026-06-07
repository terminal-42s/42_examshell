#!/bin/bash
source ../../../main/colors.sh
file1=inter.c
file2=../../../../rendu/inter/inter.c


# 1. test
    gcc -Werror -Wall -Wextra -o out1 "$file1"
    gcc -Werror -Wall -Wextra -o out2 "$file2"

    ./out1 "padinton" "paqefwtdjetyiytjneytjoeyjnejeyj" > out1.txt 2>/dev/null
    ./out2 "padinton" "paqefwtdjetyiytjneytjoeyjnejeyj" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 2. test
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"

    ./out1 "ddf6vewg64f" "gtwthgdwthdwfteewhrtag6h4ffdhsd" > out1.txt 2>/dev/null
    ./out2 "ddf6vewg64f" "gtwthgdwthdwfteewhrtag6h4ffdhsd" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 3. test
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"
    
    ./out1 "rien" "cette phrase ne cache rien" > out1.txt 2>/dev/null
    ./out2 "rien" "cette phrase ne cache rien" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 4. test
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"

    ./out1 "Oupsi" "Oups" > out1.txt 2>/dev/null
    ./out2 "Oupsi" "Oups" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 5. test 
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"

    ./out1 "Manger pour vivre" "Vivre pour manger" > out1.txt 2>/dev/null
    ./out2 "Manger pour vivre" "Vivre pour manger" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 6. test
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"

    ./out1 > out1.txt 2>/dev/null
    ./out2 > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi

# 7. test
    gcc -w -o out1 "$file1"
    gcc -w -o out2 "$file2"

    ./out1 "Too" "Many" "Arguments" > out1.txt 2>/dev/null
    ./out2 "Too" "Many" "Arguments" > out2.txt 2>/dev/null

    if ! diff -q out1.txt out2.txt >/dev/null ; then
        out1=$(cat out1.txt)
        out2=$(cat out2.txt)
        echo "$(tput setaf 1)$(tput bold)FAIL$(tput sgr 0)"
        echo "${GREEN}Expected Output:${RESET} \"$out1\""
        echo "${RED}Your Output:${RESET}     \"$out2\""
        rm out1 out2 out1.txt out2.txt 2>/dev/null
        exit 1
    fi
    

    rm out1 out2 out1.txt out2.txt 2>/dev/null
    echo "$(tput setaf 2)$(tput bold)PASSED 🎉$(tput sgr 0)"
    exit 0
