#!/usr/bin/env bash
# Roda o AG de Chu e Beasley em todas as instancias com valor de referencia
# (sac94 + gk01-gk03), 10 execucoes por instancia, em paralelo.
#
# Uso: ./rodarTudo.sh
# Os parametros podem ser trocados por variaveis de ambiente, ex.:
#   FILHOS=1000000 PARALELO=8 ./rodarTudo.sh

set -euo pipefail
cd "$(dirname "$0")"

FILHOS="${FILHOS:-200000}"
EXECUCOES="${EXECUCOES:-10}"
SEMENTE="${SEMENTE:-1}"
PARALELO="${PARALELO:-12}"

# Usa o ambiente virtual, se existir
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

if ! python -c "import scipy" 2>/dev/null; then
    echo "Aviso: scipy nao encontrado; o AG usara pesos 1/b_i em vez das duais da relaxacao linear."
    read -r -p "Continuar mesmo assim? [s/N] " resposta
    [ "$resposta" = "s" ] || exit 1
fi

# Cada rodada grava em uma pasta propria, para nao misturar com resultados anteriores
PASTA="resultados/$(date +%Y%m%d_%H%M%S)_filhos${FILHOS}"
mkdir -p "$PASTA"
export FILHOS EXECUCOES SEMENTE PASTA

INSTANCIAS=(All-MKP-Instances/sac94/*/*.dat All-MKP-Instances/gk/gk0[1-3].dat)
echo "Instancias: ${#INSTANCIAS[@]}  execucoes: $EXECUCOES  filhos: $FILHOS  paralelo: $PARALELO"
echo "Resultados em: $PASTA"
INICIO=$(date +%s)

printf '%s\n' "${INSTANCIAS[@]}" | xargs -P "$PARALELO" -I{} sh -c '
    nome=$(basename "{}" .dat)
    python teste.py "{}" --execucoes "$EXECUCOES" --semente "$SEMENTE" --filhos "$FILHOS" \
        --csv "$PASTA/$nome.csv" > "$PASTA/$nome.txt" 2>&1 \
        && echo "ok   $nome" || echo "ERRO $nome (veja $PASTA/$nome.txt)"
'

# Junta os CSVs de cada instancia em um so, mantendo apenas um cabecalho
awk 'FNR==1 && NR!=1 {next} 1' "$PASTA"/*.csv > "$PASTA/resultados.csv"

FIM=$(date +%s)
echo "Concluido em $(( (FIM - INICIO) / 60 )) min $(( (FIM - INICIO) % 60 )) s"
echo "CSV final: $PASTA/resultados.csv"

# Avisa na area de trabalho e com som (ignora se nao houver ambiente grafico)
notify-send "MKP: experimentos concluidos" "$(( (FIM - INICIO) / 60 )) min - $PASTA/resultados.csv" 2>/dev/null || true
paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || printf '\a'
