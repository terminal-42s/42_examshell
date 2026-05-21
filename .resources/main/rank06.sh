#!/bin/bash
source functions.sh
source colors.sh

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pick one random question
questions=("mini_db" "mini_serv")
random_index=$(( RANDOM % 2 ))
chosen_question="${questions[$random_index]}"

run_question() {
    question=$1
    clear
    echo "$(tput setaf 2)$(tput bold)Question: $question is being prepared...$(tput sgr0)"
    display_animation
    clear
    until bash rank06_exam_mode.sh rank06; do
        if [ $? -eq 255 ]; then
            rm -rf ../../rendu
            rm -f /tmp/.current_subject_rank06_

            exit 0
        fi

        echo "$(tput setaf 1)Test failed. Try again.$(tput sgr0)"
        read -p "Press Enter to retry $question..."
        clear
    done
    echo "$(tput setaf 2)✔️  $question passed!$(tput sgr0)"
    sleep 1
}

start_exam() {
    clear
    bash label.sh
    echo "$(tput setaf 2)$(tput bold)🧪 Welcome to the Rank06 Exam!$(tput sgr0)"
    echo "=================================================="
    echo "$(tput setaf 3)Today's question: $chosen_question$(tput sgr0)"
    echo "=================================================="
    sleep 2

    mkdir -p ../../rendu 
    run_question $chosen_question

    echo "=================================================="
    echo "$(tput setaf 2)$(tput bold)🎉 Congratulations! You passed the Rank06 exam!$(tput sgr0)"
    echo "=================================================="

    # Backup rendu folder
    if [ -d "../../rendu" ]; then
        timestamp=$(date +%Y%m%d_%H%M%S)
        mkdir -p ../../exam
        cp -r ../../rendu "../../exam/rendu_backup_$timestamp"
        echo -e "${CYAN}📁 rendu folder backed up to: exam/rendu_backup_$timestamp${RESET}"
        
        # Clean after backup
        rm -rf ../../rendu
        echo -e "${RED}🗑️  rendu folder has been cleared after successful exam.${RESET}"
    fi

    # Ask to retry
    echo
    read -rp "$(echo -e ${YELLOW}${BOLD}"Do you want to retry the exam? (y/n): "${RESET})" retry
    case "$retry" in
        y|Y)
            echo -e "${YELLOW}🔄 Restarting the exam...${RESET}"
            sleep 1
            bash rank06.sh
            ;;
        *)
            echo -e "${GREEN}Goodbye!${RESET}"
            exit 0
            ;;
    esac
}

start_exam  # Call the function
