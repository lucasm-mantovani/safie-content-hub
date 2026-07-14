#!/bin/zsh
# rodar_diario.sh — Orquestrador do pipeline diário unificado (SAFIE Blog)
# Lê agenda_publicacao do config/site.json (weekday -> lista de nichos) e,
# para cada nicho agendado hoje, roda: buscar -> gerar -> otimizar -> publicar.
#
# Preserva: gate de dia da semana, exit 75 (sem notícia) POR NICHO (não aborta os
# demais), higiene de noticia_selecionada.json (feita dentro de buscar_noticia).
#
# NOTA A2.2: scripts/buscar_noticia.py está PENDENTE (divergência de modelo de
# relevância entre os 5 blogs — aguarda decisão). Até lá, este orquestrador está
# pronto mas a etapa 1 não roda. O dry-run de A2.2 (gerar->otimizar->publicar)
# não depende deste script.

set -e

PASTA="$HOME/CLAUDE/safie-blog-unificado"
SITE="$PASTA/config/site.json"
LOG="$PASTA/logs/pipeline_$(date +%Y-%m-%d).log"
mkdir -p "$PASTA/logs"

# ── Mapa weekday -> abrev PT (seg..dom) ──
DIA_NUM=$(date +%u)  # 1=seg … 7=dom
case "$DIA_NUM" in
  1) DIA_ABREV="seg" ;; 2) DIA_ABREV="ter" ;; 3) DIA_ABREV="qua" ;;
  4) DIA_ABREV="qui" ;; 5) DIA_ABREV="sex" ;; 6) DIA_ABREV="sab" ;; 7) DIA_ABREV="dom" ;;
esac

# ── Nichos agendados hoje (lidos da agenda_publicacao) ──
NICHOS_HOJE=$(python3 -c "
import json
ag = json.load(open('$SITE')).get('agenda_publicacao', {})
print(' '.join(ag.get('$DIA_ABREV', [])))
")

if [ -z "$NICHOS_HOJE" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Hoje ($DIA_ABREV) não é dia de publicação. Encerrando." \
    >> "$PASTA/logs/skip_$(date +%Y-%m-%d).log"
  exit 0
fi

echo "=======================================" >> "$LOG"
echo "PIPELINE INICIADO: $(date) — nichos: $NICHOS_HOJE" >> "$LOG"
echo "=======================================" >> "$LOG"

cd "$PASTA"
source "$HOME/.zshrc" 2>/dev/null || true
source "$PASTA/.env" 2>/dev/null || true

# ── Loop por nicho agendado ──
for NICHO in ${(z)NICHOS_HOJE}; do
  echo "" >> "$LOG"
  echo "── NICHO: $NICHO ──" >> "$LOG"

  # Etapa 1: buscar notícia do nicho (define a categoria pela notícia encontrada)
  set +e
  python3 scripts/buscar_noticia.py --nicho "$NICHO" >> "$LOG" 2>&1
  EXIT_BUSCA=$?
  set -e
  if [ "$EXIT_BUSCA" -eq 75 ]; then
    echo "[$(date '+%H:%M:%S')] [$NICHO] Sem notícia fresca. Pulando este nicho." >> "$LOG"
    continue
  elif [ "$EXIT_BUSCA" -ne 0 ]; then
    echo "[$(date '+%H:%M:%S')] [$NICHO] ERRO em buscar_noticia (exit $EXIT_BUSCA). Pulando." >> "$LOG"
    continue
  fi

  # Categoria escolhida pela notícia (tema_slug de noticia_selecionada.json)
  CAT=$(python3 -c "import json;print(json.load(open('dados/noticia_selecionada.json')).get('tema_slug',''))" 2>/dev/null)

  # Etapa 2: gerar artigo
  echo "[$(date '+%H:%M:%S')] [$NICHO] Gerando artigo (categoria $CAT)..." >> "$LOG"
  python3 scripts/gerar_artigo.py >> "$LOG" 2>&1 || { echo "[$NICHO] falha gerar" >> "$LOG"; continue; }

  # Etapa 3: otimizar SEO/GEO
  echo "[$(date '+%H:%M:%S')] [$NICHO] Otimizando SEO/GEO..." >> "$LOG"
  python3 scripts/otimizar_seo.py >> "$LOG" 2>&1 || { echo "[$NICHO] falha seo" >> "$LOG"; continue; }

  # Etapa 4: publicar
  echo "[$(date '+%H:%M:%S')] [$NICHO] Publicando..." >> "$LOG"
  python3 scripts/publicar.py >> "$LOG" 2>&1 || { echo "[$NICHO] falha publicar" >> "$LOG"; continue; }

  echo "[$(date '+%H:%M:%S')] [$NICHO] OK." >> "$LOG"
done

echo "PIPELINE CONCLUÍDO: $(date)" >> "$LOG"
echo "=======================================" >> "$LOG"
