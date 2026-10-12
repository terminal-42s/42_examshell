#!/bin/bash
source colors.sh

rank=$1
level=$2

base_dir="$(cd "$(dirname "$0")" && pwd)"

# Set question array based on rank and level
if [[ "$rank" == "rank02" ]]; then
    if [[ "$level" == *"level0"* ]]; then
        qsub=(first_word fizzbuzz ft_putstr ft_strcpy ft_strlen ft_swap repeat_alpha rev_print rot_13 rotone search_and_replace ulstr)
    elif [[ "$level" == *"level1"* ]]; then
        qsub=(alpha_mirror camel_to_snake print_bits do_op ft_atoi ft_strcmp reverse_bits ft_strrev ft_strcspn ft_strdup inter is_power_of_2 last_word max snake_to_camel swap_bits union wdmatch)
    elif [[ "$level" == *"level2"* ]]; then
        qsub=(add_prime_sum epur_str expand_str ft_list_size ft_atoi_base ft_range ft_rrange hidenp lcm paramsum pgcd print_hex rstr_capitalizer str_capitalizer tab_mult)
    elif [[ "$level" == *"level3"* ]]; then
        qsub=(flood_fill fprime ft_itoa ft_split rev_wstr rostring ft_list_foreach sort_int_tab sort_list ft_list_remove_if)
    else
        echo "Invalid level: $level for rank02"
        exit 1
    fi
elif [[ "$rank" == "rank03" ]]; then
    if [[ "$level" == *"level1"* ]]; then
        qsub=(broken_gnl filter scanf)
    elif [[ "$level" == *"level2"* ]]; then
        qsub=(n_queens permutations powerset rip tsp)
    else
        echo "Invalid level: $level for rank03"
        exit 1
    fi
elif [[ "$rank" == "rank04" ]]; then
    if [[ "$level" == *"level1"* ]]; then
        qsub=(ft_popen picoshell sandbox)
    elif [[ "$level" == *"level2"* ]]; then
        qsub=(argo vbc)
    else
        echo "Invalid level: $level for rank04"
        exit 1
    fi
else
    echo "Invalid rank: $rank"
    exit 1
fi

# Shuffle questions manually
shuffle_array() {
    local i tmp size max rand
    size=${#qsub[*]}
    max=$(( 32768 / size * size ))

    for ((i = size - 1; i > 0; i--)); do
        while (( (rand = RANDOM) >= max )); do :; done
        rand=$(( rand % (i + 1) ))
        tmp=${qsub[i]}
        qsub[i]=${qsub[rand]}
        qsub[rand]=$tmp
    done
    shuffled=("${qsub[@]}")
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

shuffle_array
num=${#shuffled[@]}
i=0
cd "../$rank/$level/${shuffled[$i]}"

while true; do
    cd "../${shuffled[$i]}"
    mkdir -p "$base_dir/../../rendu/${shuffled[$i]}"

   # Copy question files if needed
if [[ "$rank" == "rank03" && "$level" == *"level1"* ]]; then
    if [[ "${shuffled[$i]}" == "broken_gnl" ]]; then
        if [ -f "broken_gnl.c" ]; then
            cp "broken_gnl.c" "$base_dir/../../rendu/${shuffled[$i]}/broken_gnl.c"
            touch "$base_dir/../../rendu/${shuffled[$i]}/get_next_line.c"
            touch "$base_dir/../../rendu/${shuffled[$i]}/get_next_line.h"
        fi
    elif [[ "${shuffled[$i]}" == "scanf" ]]; then
	touch "$base_dir/../../rendu/${shuffled[$i]}/ft_scanf.c"
    else
        touch "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c"
    fi
elif [[ "$rank" == "rank03" && "$level" == *"level2"* ]]; then
	if [[ "${shuffled[$i]}" == "tsp" ]]; then
		if [ -f "tsp.c" ]; then
    			cp "tsp.c" "$base_dir/../../rendu/${shuffled[$i]}/tsp.c"
    		fi
    	fi
elif [[ "$rank" == "rank04" && "$level" == *"level2"* ]]; then
    if [ -f "given.c" ]; then
        cp "given.c" "$base_dir/../../rendu/${shuffled[$i]}/given.c"
    fi
    touch "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c"
    if [[ "${shuffled[$i]}" == "vbc" ]]; then
        touch "$base_dir/../../rendu/${shuffled[$i]}/vbc.h"
    fi
else
    touch "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c"
fi

    START_TIME=$(date +%s)
    subject=$(cat sub.txt)

    # Check if all questions are completed
    if [ $i -ge $num ]; then
        clear
        echo "These questions at $level are completed."
        echo "=============================================="
        read -rp "${GREEN}${BOLD}Please press enter for return to the menu.${RESET}" enterx
        sleep 2
        cd ../../main
        bash menu.sh
        exit
    fi

    # Inner loop for testing or navigating
    while true; do
        clear
        echo -e "${WHITE}$subject${RESET}"
        echo
        echo "Please type 'test' to test code, 'next' for next or 'exit' for exit."
        echo
        read -rp "/>" input
        case $input in
            next)
                i=$((i+1))
                break
                ;;
            test)
                clear
                ./tester.sh > tester_output.log 2>&1 &
                pid=$!
                slept=0

                while [ $slept -lt 10 ] && kill -0 $pid 2>/dev/null; do
                    sleep 1
                    slept=$((slept+1))
                done

                DURATION=$(( $(date +%s) - START_TIME ))

                if kill -0 $pid 2>/dev/null; then
                    echo "$(tput setaf 1)$(tput bold)TIMEOUT$(tput sgr 0)"
                    echo "It can be because of infinite loop ∞"
                    echo "Please check your code or just try again."
                    kill $pid 2>/dev/null
                    if [ "$rank" == "rank02" ]; then
                        ask_self_assessment 0
                        python3 "$base_dir/../../db.py" record "${shuffled[$i]}" 0 "$DURATION" \
                            --code-file "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c" \
                            --trace-text "TIMEOUT: Infinite loop or process killed" \
                            --independence-status "$SELF_INDEP" \
                            --stuck-point "$SELF_STUCK" \
                            --user-notes "$SELF_NOTES" >/dev/null 2>&1
                    fi
                else
                    cat tester_output.log
                    if grep -q -E "PASSED|SUCCESS" tester_output.log; then
                        if [ "$rank" == "rank02" ]; then
                            ask_self_assessment 1
                            python3 "$base_dir/../../db.py" record "${shuffled[$i]}" 1 "$DURATION" \
                                --code-file "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c" \
                                --independence-status "$SELF_INDEP" \
                                --stuck-point "$SELF_STUCK" \
                                --user-notes "$SELF_NOTES" >/dev/null 2>&1
                        fi
                    else
                        if [ "$rank" == "rank02" ]; then
                            ask_self_assessment 0
                            python3 "$base_dir/../../db.py" record "${shuffled[$i]}" 0 "$DURATION" \
                                --code-file "$base_dir/../../rendu/${shuffled[$i]}/${shuffled[$i]}.c" \
                                --trace-file tester_output.log \
                                --independence-status "$SELF_INDEP" \
                                --stuck-point "$SELF_STUCK" \
                                --user-notes "$SELF_NOTES" >/dev/null 2>&1
                        fi
                    fi
                fi

                echo "=============================================="
                read -rp "${GREEN}${BOLD}Please press enter to continue your practice.${RESET}" enter
                break
                ;;
            menu)
                cd ../../../../
                if [ -d rendu ]; then
                    mkdir -p trace
                    cp -r rendu "trace/rendu_backup_$(date +%Y%m%d%H%M%S)"
                    rm -rf rendu
                fi
                cd .resources/main
                bash menu.sh
                exit
                ;;
            exit)
                cd ../../../../
                if [ -d rendu ]; then
                    mkdir -p trace
                    cp -r rendu "trace/rendu_backup_$(date +%Y%m%d%H%M%S)"
                    rm -rf rendu
                fi
                exit 1
                ;;
            *)
                echo "Please type 'test' to test code, 'next' for next or 'exit' to quit."
                ;;
        esac
    done
done
