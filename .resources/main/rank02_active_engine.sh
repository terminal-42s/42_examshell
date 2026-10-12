#!/bin/bash
# ==============================================================================
# 42 Examshell - Rank 02 Active Training Engine
# Handles Active Drills, Timer, Trace Capture, and SQLite stats.db integration
# ==============================================================================

source colors.sh
source functions.sh

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
DB_SCRIPT="$base_dir/../../db.py"

trap 'echo -e "\n\033[1;33m⚠️  Operação interrompida (Ctrl+C). Retornando com segurança...\033[0m"; exit 130' SIGINT SIGTERM

MODE=$1          # "sim", "pattern", "weakness"
PARAM_PATTERN=$2 # Pattern name if mode is "pattern"
PARAM_LEVEL=$3   # Level if specified

# Ensure stats.db is initialized
$PYTHON_CMD "$DB_SCRIPT" init >/dev/null 2>&1

format_seconds() {
    local sec=$1
    local min=$((sec / 60))
    local rem=$((sec % 60))
    printf "%02d:%02d" "$min" "$rem"
}

ask_self_assessment() {
    local is_success=$1
    echo
    echo -e "${MAGENTA}${BOLD}🧠 AUTOAVALIAÇÃO REFLEXIVA & MEMÓRIA MUSCULAR${RESET}"
    echo -e "${CYAN}Como foi sua autonomia nesta tentativa?${RESET}"
    echo -e "  [1] 🦾 100% Sozinho (Memória Muscular)"
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

run_exercise_session() {
    local chosen=$1
    local ex_level=$2
    local ex_patterns=$3

    local ex_dir="$base_dir/../rank02/level${ex_level}/${chosen}"
    local rendu_dir="$base_dir/../../rendu/${chosen}"

    if [ ! -d "$ex_dir" ]; then
        echo -e "${RED}Erro: Diretório do exercício não encontrado: $ex_dir${RESET}"
        return 1
    fi

    mkdir -p "$rendu_dir"
    touch "$rendu_dir/${chosen}.c"

    # Start timer
    local START_TIME=$(date +%s)
    local TRACE_LOG="/tmp/trace_${chosen}.log"
    rm -f "$TRACE_LOG"

    cd "$ex_dir" || return 1

    while true; do
        clear
        printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
        printf "${CYAN}║${RESET} ${GREEN}${BOLD}EXERCÍCIO:${RESET} %-22s ${YELLOW}${BOLD}NÍVEL:${RESET} Level %-3s ${BLUE}${BOLD}PADRÕES:${RESET} %-19s ${CYAN}║${RESET}\n" "$chosen" "$ex_level" "$ex_patterns"
        printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"
        echo
        if [ -f "sub.txt" ]; then
            cat sub.txt
        else
            echo "Subject não encontrado."
        fi
        echo
        printf "${CYAN}%s${RESET}\n" "─────────────────────────────────────────────────────────────────────────────"
        local CURRENT_TIME=$(date +%s)
        local ELAPSED=$((CURRENT_TIME - START_TIME))
        echo -e "⏱️  Tempo decorrido: ${BOLD}$(format_seconds $ELAPSED)${RESET} | Pasta de trabalho: ${BOLD}rendu/${chosen}/${chosen}.c${RESET}"
        echo -e "${YELLOW}Comandos disponíveis:${RESET}"
        echo -e "  • ${GREEN}${BOLD}test${RESET}  : Compilar e rodar testes do Moulinette (salva no banco)"
        echo -e "  • ${BLUE}${BOLD}trace${RESET} : Ver o último log de erro gravado para esta questão"
        echo -e "  • ${MAGENTA}${BOLD}stats${RESET} : Abrir dashboard de estatísticas"
        echo -e "  • ${YELLOW}${BOLD}next${RESET}  : Pular questão atual"
        echo -e "  • ${RED}${BOLD}exit${RESET}  : Sair para o menu"
        echo

        read -rp "/> " user_cmd
        case "$user_cmd" in
            test)
                clear
                echo -e "${CYAN}${BOLD}===> Executando testes oficiais (tester.sh)...${RESET}\n"
                
                # Execute tester and intercept entire output to trace log
                rm -f "$TRACE_LOG"
                ./tester.sh 2>&1 | tee "$TRACE_LOG"
                local TEST_EXIT=${PIPESTATUS[0]}

                local END_TIME=$(date +%s)
                local DURATION=$((END_TIME - START_TIME))

                echo
                if [ $TEST_EXIT -eq 0 ] || grep -q -E "PASSED|SUCCESS" "$TRACE_LOG"; then
                    echo -e "${GREEN}${BOLD}🎉 EXCELENTE! VOCÊ PASSOU EM TODOS OS TESTES!${RESET}"
                    echo -e "${GREEN}Tempo total de resolução: $(format_seconds $DURATION)${RESET}"

                    ask_self_assessment 1

                    # Record successful attempt in SQLite with submitted code and self-assessment
                    $PYTHON_CMD "$DB_SCRIPT" record "$chosen" 1 "$DURATION" \
                        --code-file "$rendu_dir/${chosen}.c" \
                        --independence-status "$SELF_INDEP" \
                        --stuck-point "$SELF_STUCK" \
                        --user-notes "$SELF_NOTES" >/dev/null 2>&1
                    echo -e "${CYAN}💾 Tentativa de sucesso e autoavaliação gravadas em stats.db!${RESET}\n"
                    read -rp "Pressione [Enter] para continuar..." dummy
                    return 0
                else
                    echo -e "${RED}${BOLD}❌ FALHA NOS TESTES / COMPILAÇÃO.${RESET}"
                    echo -e "${YELLOW}Tempo até a falha: $(format_seconds $DURATION)${RESET}"

                    ask_self_assessment 0

                    # Record failed attempt with full error trace, submitted code, and self-assessment in SQLite
                    $PYTHON_CMD "$DB_SCRIPT" record "$chosen" 0 "$DURATION" \
                        --trace-file "$TRACE_LOG" \
                        --code-file "$rendu_dir/${chosen}.c" \
                        --independence-status "$SELF_INDEP" \
                        --stuck-point "$SELF_STUCK" \
                        --user-notes "$SELF_NOTES" >/dev/null 2>&1
                    echo -e "${CYAN}💾 Trace de erro e autoavaliação persistidos em stats.db.${RESET}\n"
                    echo -e "Você pode editar seu código em ${BOLD}rendu/${chosen}/${chosen}.c${RESET} e digitar 'test' novamente."
                    read -rp "Pressione [Enter] para voltar ao enunciado..." dummy
                fi
                ;;
            trace)
                clear
                echo -e "${BLUE}${BOLD}=== ÚLTIMO TRACE DE ERRO: ${chosen} ===${RESET}\n"
                if [ -f "$TRACE_LOG" ] && [ -s "$TRACE_LOG" ]; then
                    cat "$TRACE_LOG"
                else
                    $PYTHON_CMD "$DB_SCRIPT" show-trace "$chosen"
                fi
                echo
                read -rp "Pressione [Enter] para voltar ao exercício..." dummy
                ;;
            stats)
                clear
                $PYTHON_CMD "$DB_SCRIPT" stats
                read -rp "Pressione [Enter] para retornar ao exercício..." dummy
                ;;
            next)
                echo -e "${YELLOW}Pulando exercício ${chosen}...${RESET}"
                sleep 1
                return 2
                ;;
            exit|quit)
                echo -e "Saindo da sessão..."
                sleep 1
                return 255
                ;;
            *)
                echo -e "${RED}Comando não reconhecido. Use test, trace, stats, next ou exit.${RESET}"
                sleep 1
                ;;
        esac
    done
}

# ==============================================================================
# Modo 1: Simulado Clássico (1 questão por nível sequencialmente)
# ==============================================================================
run_sim_mode() {
    clear
    printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
    printf "${CYAN}║${RESET} ${GREEN}${BOLD}             🧪 SIMULADO CLÁSSICO DE EXAME (RANK 02)               ${RESET} ${CYAN}║${RESET}\n"
    printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "Regras: Você resolverá 1 questão de cada nível (Level 0 ➔ 1 ➔ 2 ➔ 3)."
    echo -e "Todas as submissões e tempos serão registrados automaticamente no banco."
    echo
    read -rp "Pressione [Enter] para iniciar o Simulado..." dummy

    for lvl in 0 1 2 3; do
        clear
        echo -e "${YELLOW}${BOLD}=== Sorteando questão para o Level $lvl... ===${RESET}"
        display_animation 2>/dev/null
        
        local pick_info=$($PYTHON_CMD "$DB_SCRIPT" pick --mode sim --level $lvl)
        local chosen=$(echo "$pick_info" | cut -d':' -f1)
        local chosen_lvl=$(echo "$pick_info" | cut -d':' -f2)
        local chosen_pat=$(echo "$pick_info" | cut -d':' -f3-)

        run_exercise_session "$chosen" "$chosen_lvl" "$chosen_pat"
        local res=$?
        if [ $res -eq 255 ]; then
            return 255
        elif [ $res -ne 0 ]; then
            echo -e "${YELLOW}Passando para o próximo nível...${RESET}"
            sleep 1
        fi
    done

    clear
    echo -e "${GREEN}${BOLD}🏆 PARABÉNS! VOCÊ COMPLETOU O SIMULADO DO RANK 02!${RESET}\n"
    $PYTHON_CMD "$DB_SCRIPT" stats
    read -rp "Pressione [Enter] para retornar ao menu..." dummy
}

# ==============================================================================
# Modo 2: Treino por Padrão Técnico (Pattern Drill)
# ==============================================================================
run_pattern_drill_mode() {
    local target_pattern="$PARAM_PATTERN"

    if [ -z "$target_pattern" ]; then
        clear
        printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
        printf "${CYAN}║${RESET} ${GREEN}${BOLD}            🎯 TREINO POR PADRÃO TÉCNICO (PATTERN DRILL)           ${RESET} ${CYAN}║${RESET}\n"
        printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"
        echo -e "Escolha o padrão técnico que deseja treinar:\n"

        # Use mapfile to preserve whitespace in multi-word pattern names
        mapfile -t patterns < <($PYTHON_CMD "$DB_SCRIPT" list-patterns)
        local count=${#patterns[@]}

        for i in "${!patterns[@]}"; do
            printf "${YELLOW}%2d)${RESET} %s\n" "$((i + 1))" "${patterns[$i]}"
        done
        echo
        printf "${GREEN}${BOLD}Escolha o número do padrão (1-%d) ou 'exit': ${RESET}" "$count"
        read -r pat_idx

        if [[ "$pat_idx" =~ ^[0-9]+$ ]] && [ "$pat_idx" -ge 1 ] && [ "$pat_idx" -le "$count" ]; then
            target_pattern="${patterns[$((pat_idx - 1))]}"
        else
            return
        fi
    fi

    clear
    echo -e "${CYAN}Iniciando Treino focado no padrão: ${BOLD}${target_pattern}${RESET}...\n"
    echo -e "${YELLOW}Questões cadastradas para '${target_pattern}':${RESET}"
    $PYTHON_CMD "$DB_SCRIPT" get-by-pattern "$target_pattern" | while IFS=':' read -r ex_id ex_lvl ex_pats; do
        echo -e "  • ${GREEN}${ex_id}${RESET} (Level ${ex_lvl}) - ${BLUE}${ex_pats}${RESET}"
    done
    echo
    read -rp "Pressione [Enter] para iniciar..." dummy

    while true; do
        local pick_info=$($PYTHON_CMD "$DB_SCRIPT" pick --mode pattern --pattern "$target_pattern" 2>/dev/null)
        if [[ "$pick_info" == ERROR* ]] || [ -z "$pick_info" ]; then
            echo -e "${RED}Nenhuma questão encontrada para o padrão '$target_pattern'.${RESET}"
            sleep 2
            break
        fi

        local chosen=$(echo "$pick_info" | cut -d':' -f1)
        local chosen_lvl=$(echo "$pick_info" | cut -d':' -f2)
        local chosen_pat=$(echo "$pick_info" | cut -d':' -f3-)

        run_exercise_session "$chosen" "$chosen_lvl" "$chosen_pat"
        local res=$?
        if [ $res -eq 255 ]; then
            break
        fi

        echo
        read -rp "Continuar treinando o padrão '$target_pattern'? (s/n): " cont
        if [[ "$cont" != "s" && "$cont" != "S" ]]; then
            break
        fi
    done
}

# ==============================================================================
# Modo 3: Modo Fraquezas (Weakness Focus / Spaced Repetition)
# ==============================================================================
run_weakness_mode() {
    clear
    printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
    printf "${CYAN}║${RESET} ${RED}${BOLD}            🧠 MODO FRAQUEZAS & REPETIÇÃO ESPAÇADA                 ${RESET} ${CYAN}║${RESET}\n"
    printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "O sistema seleciona automaticamente as questões com maior prioridade de treino:"
    echo -e "  1. Questões nunca tentadas (0 tentativas)."
    echo -e "  2. Questões com menor taxa de acerto (mais falhas)."
    echo -e "  3. Questões com maior tempo sem prática.\n"
    read -rp "Pressione [Enter] para iniciar a sessão de foco..." dummy

    while true; do
        local pick_info=$($PYTHON_CMD "$DB_SCRIPT" pick --mode weakness 2>/dev/null)
        if [[ "$pick_info" == ERROR* ]] || [ -z "$pick_info" ]; then
            echo -e "${RED}Fila de fraquezas indisponível.${RESET}"
            sleep 2
            break
        fi

        local chosen=$(echo "$pick_info" | cut -d':' -f1)
        local chosen_lvl=$(echo "$pick_info" | cut -d':' -f2)
        local chosen_pat=$(echo "$pick_info" | cut -d':' -f3-)

        run_exercise_session "$chosen" "$chosen_lvl" "$chosen_pat"
        local res=$?
        if [ $res -eq 255 ]; then
            break
        fi

        echo
        read -rp "Próxima questão prioritária da fila? (s/n): " cont
        if [[ "$cont" != "s" && "$cont" != "S" ]]; then
            break
        fi
    done
}

# ==============================================================================
# Modo 4: Fila Configurável / Treino Customizado (Custom Drill Queue)
# ==============================================================================
run_custom_queue_mode() {
    local target_source="$PARAM_PATTERN"
    local queue_exercises=()

    clear
    printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
    printf "${CYAN}║${RESET} ${GREEN}${BOLD}           🎯 MODO TREINO CUSTOMIZADO (CUSTOM DRILL QUEUE)           ${RESET} ${CYAN}║${RESET}\n"
    printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"

    if [ -n "$target_source" ] && [ -f "$target_source" ]; then
        echo -e "Carregando fila do arquivo: ${BOLD}${target_source}${RESET}..."
        while IFS=':' read -r ex_id ex_lvl ex_pats; do
            [ -n "$ex_id" ] && queue_exercises+=("$ex_id:$ex_lvl:$ex_pats")
        done < <($PYTHON_CMD "$DB_SCRIPT" get-queue "$target_source")
    elif [ -n "$target_source" ] && [[ "$target_source" =~ ^[0-9]+$ ]]; then
        echo -e "Carregando fila salva ID #${target_source}..."
        while IFS=':' read -r ex_id ex_lvl ex_pats; do
            [ -n "$ex_id" ] && queue_exercises+=("$ex_id:$ex_lvl:$ex_pats")
        done < <($PYTHON_CMD "$DB_SCRIPT" get-queue "$target_source")
    else
        echo -e "Como deseja carregar ou montar seu treino customizado?"
        echo -e "  [1] 📂 Carregar a última fila salva no sistema"
        echo -e "  [2] 📋 Selecionar uma fila salva no banco de dados"
        echo -e "  [3] 📄 Carregar arquivo JSON de fila (ex: custom_queue.json)"
        echo -e "  [4] ✍️  Montar nova sequência personalizada agora"
        echo -e "  [q] Sair"
        echo
        read -rp "Opção (1-4): " q_choice

        case "$q_choice" in
            1)
                while IFS=':' read -r ex_id ex_lvl ex_pats; do
                    [ -n "$ex_id" ] && queue_exercises+=("$ex_id:$ex_lvl:$ex_pats")
                done < <($PYTHON_CMD "$DB_SCRIPT" get-queue "latest" 2>/dev/null)
                ;;
            2)
                clear
                echo -e "${CYAN}=== Filas Salvas no Sistema ===${RESET}"
                $PYTHON_CMD "$DB_SCRIPT" list-queues
                echo
                read -rp "Digite o ID da fila desejada: " chosen_qid
                if [ -n "$chosen_qid" ]; then
                    while IFS=':' read -r ex_id ex_lvl ex_pats; do
                        [ -n "$ex_id" ] && queue_exercises+=("$ex_id:$ex_lvl:$ex_pats")
                    done < <($PYTHON_CMD "$DB_SCRIPT" get-queue "$chosen_qid" 2>/dev/null)
                fi
                ;;
            3)
                read -rp "Caminho do arquivo JSON da fila: " json_path
                if [ -f "$json_path" ]; then
                    while IFS=':' read -r ex_id ex_lvl ex_pats; do
                        [ -n "$ex_id" ] && queue_exercises+=("$ex_id:$ex_lvl:$ex_pats")
                    done < <($PYTHON_CMD "$DB_SCRIPT" get-queue "$json_path" 2>/dev/null)
                else
                    echo -e "${RED}Arquivo '$json_path' não encontrado.${RESET}"
                    sleep 2
                    return
                fi
                ;;
            4)
                clear
                echo -e "${CYAN}=== Montar Sequência Personalizada ===${RESET}"
                echo -e "Digite os nomes dos exercícios na ordem desejada (separados por espaço)."
                echo -e "Exemplo: first_word repeat_alpha ft_strdup inter ft_split\n"
                read -rp "Exercícios: " -a custom_names
                for name in "${custom_names[@]}"; do
                    local info=$($PYTHON_CMD "$DB_SCRIPT" get-exercise-info "$name" 2>/dev/null)
                    if [ -n "$info" ]; then
                        queue_exercises+=("$info")
                    else
                        echo -e "${YELLOW}Aviso: Exercício '$name' não reconhecido. Adicionando como Level 0.${RESET}"
                        queue_exercises+=("$name:0:C Standard")
                    fi
                done
                ;;
            *)
                return
                ;;
        esac
    fi

    local total_in_queue=${#queue_exercises[@]}
    if [ "$total_in_queue" -eq 0 ]; then
        echo -e "${RED}Nenhum exercício encontrado na fila customizada.${RESET}"
        sleep 2
        return
    fi

    clear
    echo -e "${GREEN}${BOLD}📋 Sequência do Treino Customizado (${total_in_queue} exercícios):${RESET}\n"
    local idx=1
    for item in "${queue_exercises[@]}"; do
        local q_name=$(echo "$item" | cut -d':' -f1)
        local q_lvl=$(echo "$item" | cut -d':' -f2)
        local q_pat=$(echo "$item" | cut -d':' -f3-)
        echo -e "  ${idx}. ${BOLD}${q_name}${RESET} [Level ${q_lvl}] - ${BLUE}${q_pat}${RESET}"
        idx=$((idx + 1))
    done
    echo
    read -rp "Pressione [Enter] para iniciar o treino na ordem configurada..." dummy

    local current_idx=1
    local passed_count=0
    local failed_count=0

    for item in "${queue_exercises[@]}"; do
        local chosen=$(echo "$item" | cut -d':' -f1)
        local chosen_lvl=$(echo "$item" | cut -d':' -f2)
        local chosen_pat=$(echo "$item" | cut -d':' -f3-)

        echo -e "\n${CYAN}>>> Exercício ${current_idx}/${total_in_queue}: ${BOLD}${chosen}${RESET} (Level ${chosen_lvl})\n"
        run_exercise_session "$chosen" "$chosen_lvl" "$chosen_pat"
        local res=$?

        if [ $res -eq 255 ]; then
            echo -e "\n${YELLOW}Sessão da fila customizada interrompida pelo usuário.${RESET}"
            break
        elif [ $res -eq 0 ]; then
            passed_count=$((passed_count + 1))
        else
            failed_count=$((failed_count + 1))
        fi

        current_idx=$((current_idx + 1))
        if [ $current_idx -le $total_in_queue ]; then
            echo
            read -rp "Próximo exercício da fila (${current_idx}/${total_in_queue})? [Enter para continuar, 'q' para parar]: " next_opt
            if [[ "$next_opt" == "q" || "$next_opt" == "Q" ]]; then
                break
            fi
        fi
    done

    clear
    printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════════════╗"
    printf "${CYAN}║${RESET} ${GREEN}${BOLD}             🎉 SESSÃO DE TREINO CUSTOMIZADO FINALIZADA!          ${RESET} ${CYAN}║${RESET}\n"
    printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "Total planejado: ${BOLD}${total_in_queue}${RESET}"
    echo -e "Executados: ${BOLD}$((passed_count + failed_count))${RESET}"
    echo -e "Aprovados: ${GREEN}${BOLD}${passed_count}${RESET}"
    echo -e "Falhas/Pendentes: ${RED}${BOLD}${failed_count}${RESET}\n"
    read -rp "Pressione [Enter] para retornar ao menu..." dummy
}

# ==============================================================================
# Router
# ==============================================================================
case "$MODE" in
    sim)
        run_sim_mode
        ;;
    pattern)
        run_pattern_drill_mode
        ;;
    weakness)
        run_weakness_mode
        ;;
    custom)
        run_custom_queue_mode
        ;;
    *)
        echo "Uso: $0 <sim|pattern|weakness|custom> [target_file|pattern_name] [level]"
        exit 1
        ;;
esac
