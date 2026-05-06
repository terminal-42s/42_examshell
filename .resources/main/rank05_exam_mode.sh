#!/bin/bash
source colors.sh

rank=$1
level=$2

# Save base directory (where script was launched from)
base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Centralized temp file to track subject
subject_file="/tmp/.current_subject_${rank}_${level}"

# Define subject pool
get_subjects() {
    case "$level" in
        level1)
            echo "bigint polyset vect2"
            ;;
        level2)
            echo "bsq life"
            ;;
        *)
            echo ""
            ;;
    esac
}

# Pick a new random subject
pick_new_subject() {
    subjects_list=$(get_subjects)
    IFS=' ' read -r -a qsub <<< "$subjects_list"
    count=${#qsub[@]}
    random_index=$(( RANDOM % count ))
    chosen="${qsub[$random_index]}"
    echo "$chosen" > "$subject_file"
}

# Prepare the subject folder and files
prepare_subject() {
    mkdir -p "$base_dir/../../rendu/$chosen"

    if [[ "$level" == "level2" ]]; then
        # Level2 → create .c and .h only if missing
        [ ! -f "$base_dir/../../rendu/$chosen/$chosen.c" ] && touch "$base_dir/../../rendu/$chosen/$chosen.c"
        [ ! -f "$base_dir/../../rendu/$chosen/$chosen.h" ] && touch "$base_dir/../../rendu/$chosen/$chosen.h"
    else
        # Level1 → create .cpp and .hpp only if missing
        [ ! -f "$base_dir/../../rendu/$chosen/$chosen.cpp" ] && touch "$base_dir/../../rendu/$chosen/$chosen.cpp"
        [ ! -f "$base_dir/../../rendu/$chosen/$chosen.hpp" ] && touch "$base_dir/../../rendu/$chosen/$chosen.hpp"
    fi

    # Special case: Polyset for rank05 level1
    if [[ "$rank" == "rank05" && "$level" == "level1" && "$chosen" == "polyset" ]]; then
        src_subject_dir="$base_dir/../rank05/level1/polyset/subject"
        dest_dir="$base_dir/../../rendu/polyset/subject"
        if [ -d "$src_subject_dir" ]; then
            mkdir -p "$dest_dir"
            cp -r "$src_subject_dir" "$dest_dir"
        fi
    fi

    # Go to the subject folder dynamically
    cd "$base_dir/../$rank/$level/$chosen" || {
        echo -e "${RED}Subject folder not found.${RESET}"
        exit 1
    }

    clear
    echo -e "${CYAN}${BOLD}Your subject: $chosen${RESET}"
    echo "=================================================="
    cat sub.txt
    echo
    echo -e "=================================================="
    echo -e "${YELLOW}Type 'test' to test your code, 'next' to get a new question, or 'exit' to quit.${RESET}"
}

# Initial subject selection
if [ -f "$subject_file" ]; then
    chosen=$(cat "$subject_file")
    echo -e "${BLUE}🔁 Resuming with previously chosen subject: $chosen${RESET}"
else
    pick_new_subject
fi

prepare_subject

# Command loop
while true; do
    read -rp "/> " input
    case "$input" in
        test)
            clear
            echo -e "${GREEN}Running tester.sh...${RESET}"
            output=$(./tester.sh 2>&1)
            echo "$output" | tee tester_output.log

            if echo "$output" | grep -q "ALL TESTS PASSED"; then
                echo -e "${GREEN}${BOLD}✔️  Passed!${RESET}"
                rm -f "$subject_file"
                sleep 1
                exit 0
            else
                echo -e "${RED}${BOLD}❌  Failed.${RESET}"
                sleep 1
                exit 1
            fi
            ;;
        next)
            echo -e "${BLUE}🔄 Picking a new subject...${RESET}"
            pick_new_subject
            chosen=$(cat "$subject_file")
            prepare_subject
            ;;
        exit)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Please type 'test' to test code, 'next' for next or 'exit' for exit."
            ;;
    esac
done
