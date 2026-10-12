#!/bin/bash
source colors.sh

rank=$1
level=$2

# Save base directory (where script was launched from)
base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Centralized temp file to track subject
subject_file="/tmp/.current_subject_${rank}_${level}"

# Define subject pool using case statement instead of associative array
get_subjects() {
    case "$level" in
        level0)
            echo "first_word fizzbuzz ft_putstr ft_strcpy ft_strlen ft_swap repeat_alpha rev_print rot_13 rotone search_and_replace ulstr"
            ;;
        level1)
            echo "alpha_mirror camel_to_snake print_bits do_op ft_atoi ft_strcmp reverse_bits ft_strrev ft_strcspn ft_strdup inter is_power_of_2 last_word max snake_to_camel swap_bits union wdmatch"
            ;;
        level2)
            echo "add_prime_sum epur_str expand_str ft_list_size ft_atoi_base ft_range ft_rrange hidenp lcm paramsum pgcd print_hex rstr_capitalizer str_capitalizer tab_mult"
            ;;
        level3)
            echo "flood_fill fprime ft_itoa ft_split rev_wstr rostring ft_list_foreach sort_int_tab sort_list ft_list_remove_if"
            ;;
        *)
            echo ""
            ;;
    esac
}

ask_self_assessment() {
    local is_success=$1
    echo
    echo -e "${MAGENTA}${BOLD}🧠 AUTOAVALIAÇÃO REFLEXIVA & MEMÓRIA MUSCULAR${RESET}"
    echo -e "${CYAN}Como foi sua autonomia nesta tentativa?${RESET}"
    echo -e "  [1] 🦾 100% Sozinho (Sem consulta)"
    echo -e "  [2] 🔍 Precisei pesquisar / consultar material"
    echo -e "  [Pressione Enter para pular]"
    read -rp "Sua escolha (1/2): " indep_choice

    local independence=""
    if [ "$indep_choice" = "1" ]; then
        independence="alone"
    elif [ "$indep_choice" = "2" ]; then
        independence="searched"
    fi

    local stuck_point=""
    if [ "$is_success" -eq 0 ] || [ "$independence" = "searched" ]; then
        echo -e "${YELLOW}Qual foi o ponto principal de bloqueio ou dúvida? (Ex: Malloc/Free, Off-by-one, ASCII wrap, Segfault, Lógica do loop)${RESET}"
        read -rp "Bloqueio [Enter para pular]: " stuck_point
    fi

    echo -e "${BLUE}Alguma reflexão, anotação ou insight pessoal?${RESET}"
    read -rp "Notas [Enter para pular]: " user_notes

    SELF_INDEP="$independence"
    SELF_STUCK="$stuck_point"
    SELF_NOTES="$user_notes"
}

pick_new_subject() {
    subjects_list=$(get_subjects)
    IFS=' ' read -r -a qsub <<< "$subjects_list"
    count=${#qsub[@]}
    random_index=$(( RANDOM % count ))
    chosen="${qsub[$random_index]}"
    echo "$chosen" > "$subject_file"
}

prepare_subject() {
    START_TIME=$(date +%s)
    mkdir -p "$base_dir/../../rendu/$chosen"
    touch "$base_dir/../../rendu/$chosen/$chosen.c"

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
            ./tester.sh > tester_output.log 2>&1 &
            pid=$!
            slept=0
            while [ $slept -lt 10 ] && kill -0 $pid 2>/dev/null; do
                sleep 1
                slept=$((slept+1))
            done
            
            DURATION=$(( $(date +%s) - START_TIME ))

            if kill -0 $pid 2>/dev/null; then
                echo -e "${RED}${BOLD}TIMEOUT${RESET}"
                echo "It can be because of infinite loop "
                echo "Please check your code or just try again."
                pkill -P $pid 2>/dev/null
                killall -9 out1 out2 2>/dev/null
                kill -9 $pid 2>/dev/null
                ask_self_assessment 0
                python3 "$base_dir/../../db.py" record "$chosen" 0 "$DURATION" \
                    --code-file "$base_dir/../../rendu/$chosen/$chosen.c" \
                    --trace-text "TIMEOUT: Infinite loop or process killed after 10s" \
                    --independence-status "$SELF_INDEP" \
                    --stuck-point "$SELF_STUCK" \
                    --user-notes "$SELF_NOTES" >/dev/null 2>&1
                sleep 1
                exit 1
            fi
            
            output=$(cat tester_output.log)
            echo "$output" | tee tester_output.log

            if echo "$output" | grep -q -E "PASSED|SUCCESS"; then
                echo -e "${GREEN}${BOLD}✔️  Passed!${RESET}"
                ask_self_assessment 1
                python3 "$base_dir/../../db.py" record "$chosen" 1 "$DURATION" \
                    --code-file "$base_dir/../../rendu/$chosen/$chosen.c" \
                    --independence-status "$SELF_INDEP" \
                    --stuck-point "$SELF_STUCK" \
                    --user-notes "$SELF_NOTES" >/dev/null 2>&1
                rm -f "$subject_file"
                sleep 1
                exit 0
            else
                echo -e "${RED}${BOLD}❌  Failed.${RESET}"
                ask_self_assessment 0
                python3 "$base_dir/../../db.py" record "$chosen" 0 "$DURATION" \
                    --code-file "$base_dir/../../rendu/$chosen/$chosen.c" \
                    --trace-file tester_output.log \
                    --independence-status "$SELF_INDEP" \
                    --stuck-point "$SELF_STUCK" \
                    --user-notes "$SELF_NOTES" >/dev/null 2>&1
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
            exit 255 
            ;;
        *)
            echo "Please type 'test' to test code, 'next' for next or 'exit' for exit."
            ;;
    esac
done
