#!/bin/bash
source colors.sh

base_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
DB_SCRIPT="$base_dir/../../db.py"

clear
printf "${CYAN}%s${RESET}\n" "╔═══════════════════════════════════════════════════════════════════╗"
printf "${BLUE}%s${GREEN}%s${BLUE}%s${RESET}\n" "║" "         🧠 EXAM RANK 02 - ACTIVE LEARNING & PATTERNS            " "║"
printf "${CYAN}%s${RESET}\n" "╚═══════════════════════════════════════════════════════════════════╝"
printf "${YELLOW}${BOLD}%s${RESET}\n" "1. 🧪 Modo Exame Padrão (Simulado - 1 por nível)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "2. 🎯 Treino por Padrão Técnico (Pattern Drill - 13 Padrões)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "3. ⚡ Modo Fraquezas (Weakness Focus & Repetição Espaçada)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "4. 📋 Treino Customizado (Fila Personalizada / Sequência sob Medida)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "5. 📊 Dashboard de Estatísticas & Traces no Terminal"
printf "${YELLOW}${BOLD}%s${RESET}\n" "6. 🌐 Abrir Dashboard Web & Tutor IA (Navegador - Porta 5000)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "7. 📁 Modo Clássico por Nível (Level Mode)"
printf "${YELLOW}${BOLD}%s${RESET}\n" "8. 🔙 Voltar ao Menu Principal"
echo
printf "${GREEN}${BOLD}Escolha uma opção (1-8): ${RESET}"
read -r rank02_opt

case $rank02_opt in
    1)
        bash rank02_active_engine.sh sim
        bash rank02_menu.sh
        ;;
    2)
        bash rank02_active_engine.sh pattern
        bash rank02_menu.sh
        ;;
    3)
        bash rank02_active_engine.sh weakness
        bash rank02_menu.sh
        ;;
    4)
        bash rank02_active_engine.sh custom
        bash rank02_menu.sh
        ;;
    5)
        clear
        $PYTHON_CMD "$DB_SCRIPT" stats
        echo
        printf "${CYAN}%s${RESET}\n" "Deseja inspecionar traces de erro detalhados? (s/n): "
        read -r view_traces
        if [[ "$view_traces" == "s" || "$view_traces" == "S" ]]; then
            clear
            $PYTHON_CMD "$DB_SCRIPT" stats --traces
            echo
            read -rp "Pressione [Enter] para retornar ao menu..." dummy
        fi
        bash rank02_menu.sh
        ;;
    6)
        clear
        echo -e "${CYAN}Iniciando Dashboard Web em segundo plano...${RESET}"
        bash "$base_dir/../../dashboard.sh" &
        sleep 2
        bash rank02_menu.sh
        ;;
    7)
        bash rank02.sh
        ;;
    8)
        bash intro.sh
        ;;
    *)
        echo "Opção inválida. Por favor digite um número entre 1 e 8."
        sleep 1
        bash rank02_menu.sh
        ;;
esac