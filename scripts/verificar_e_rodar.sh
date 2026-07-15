#!/bin/zsh
# verificar_e_rodar.sh — Watchdog do pipeline unificado (SAFIE Blog).
# Roda a cada 30 min via launchd. Só dispara rodar_diario.sh se:
#   1. Hoje é dia de publicação (config/site.json -> agenda_publicacao)
#   2. Ainda não publicou hoje (artigos/indice.json não contém a data de hoje)
#   3. Tentativas do dia < 3 (marcador dados/watchdog_tentativas_<DATA>.json)
#   4. Estamos numa janela (manha 06-08 / tarde 12-14 / noite 17-19)
#   5. Há internet
# É catch-up: o diário das 07:00 é o disparo primário; o watchdog cobre o caso
# de a máquina estar dormindo/offline às 07:00. Self-locating (roda no checkout
# onde estiver — pós-cutover, na main ~/CLAUDE/Content-Hub-SAFIE).

cd "$(dirname "$0")/.." || exit 1
PASTA="$(pwd)"

# 1. Gate de dia da semana (agenda_publicacao do site.json)
DIA_ABREV=$(python3 -c "print(['seg','ter','qua','qui','sex','sab','dom'][$(date +%u)-1])")
EH_DIA=$(python3 -c "
import json
ag = json.load(open('$PASTA/config/site.json')).get('agenda_publicacao', {})
print('sim' if ag.get('$DIA_ABREV') else 'nao')
")
[ "$EH_DIA" = "sim" ] || exit 0

# 2. Já publicou hoje?
HOJE=$(date +%Y-%m-%d)
if [ -f artigos/indice.json ] && grep -q "\"$HOJE" artigos/indice.json; then
  exit 0
fi

# 3. Tentativas hoje (< 3)
MARCADOR="dados/watchdog_tentativas_${HOJE}.json"
TENTATIVAS=$(python3 -c "
import json
try: print(len(json.load(open('$MARCADOR')).get('tentativas', [])))
except Exception: print(0)
")
[ "$TENTATIVAS" -ge 3 ] && exit 0

# 4. Janela
HORA=$(date +%H)
case "$HORA" in
  06|07|08) JANELA="manha" ;;
  12|13|14) JANELA="tarde" ;;
  17|18|19) JANELA="noite" ;;
  *) exit 0 ;;
esac

# 5. Janela já tentada?
JA=$(python3 -c "
import json
try: d=json.load(open('$MARCADOR')); print('sim' if any(t.get('janela')=='$JANELA' for t in d.get('tentativas',[])) else 'nao')
except Exception: print('nao')
")
[ "$JA" = "sim" ] && exit 0

# 6. Internet?
curl -s --max-time 5 https://8.8.8.8 > /dev/null 2>&1 || exit 0

# 7. Registra a tentativa e dispara o pipeline
python3 -c "
import json, datetime
try: d=json.load(open('$MARCADOR'))
except Exception: d={'tentativas':[]}
d['tentativas'].append({'janela':'$JANELA','hora':datetime.datetime.now().isoformat()})
json.dump(d, open('$MARCADOR','w'), ensure_ascii=False, indent=2)
"
./rodar_diario.sh
