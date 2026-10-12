#!/bin/bash
# ==============================================================================
# 42 Exam Shell - Entry Point with Active Training & CLI Flags
# ==============================================================================

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$1" in
    --stats)
        python3 "$BASE_DIR/db.py" stats "${@:2}"
        ;;
    --sim)
        cd "$BASE_DIR/.resources/main" && bash rank02_active_engine.sh sim
        ;;
    --pattern)
        if [ -z "$2" ]; then
            cd "$BASE_DIR/.resources/main" && bash rank02_active_engine.sh pattern
        else
            cd "$BASE_DIR/.resources/main" && bash rank02_active_engine.sh pattern "$2"
        fi
        ;;
    --review|--weakness)
        cd "$BASE_DIR/.resources/main" && bash rank02_active_engine.sh weakness
        ;;
    --custom)
        cd "$BASE_DIR/.resources/main" && bash rank02_active_engine.sh custom "$2"
        ;;
    --dashboard|--web)
        bash "$BASE_DIR/dashboard.sh"
        ;;
    --help|-h)
        echo "42 Examshell - Plataforma de Treino Ativo & Padrões Técnicos (Rank 02)"
        echo ""
        echo "Uso:"
        echo "  bash exam.sh                      # Iniciar menu interativo"
        echo "  bash exam.sh --custom [fila.json] # Modo Fila Customizada (sequência personalizada)"
        echo "  bash exam.sh --sim                # Modo Simulado Clássico (1 por nível)"
        echo "  bash exam.sh --pattern <id>       # Treino focado por Padrão Técnico"
        echo "  bash exam.sh --review             # Modo Fraquezas & Repetição Espaçada"
        echo "  bash exam.sh --stats              # Exibir Dashboard de Estatísticas no terminal"
        echo "  bash exam.sh --dashboard          # Iniciar Dashboard Web com Tutor IA (porta 5000)"
        ;;
    *)
        cd "$BASE_DIR/.resources/main" && bash menu.sh
        ;;
esac
