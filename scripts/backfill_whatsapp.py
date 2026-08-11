"""
backfill_whatsapp.py — troca o número de WhatsApp da SAFIE na URL wa.me do CTA
"Falar com a SAFIE" nos artigos JÁ PUBLICADOS (artigos/*.html).

A fonte (templates/artigo.html e assets/js/widget-whatsapp.js) é trocada à parte;
este script cobre apenas os HTMLs baked. Idempotente: artigo já com o número novo
(ou sem CTA, como artigos/index.html) não é tocado.

Uso:
  python3 scripts/backfill_whatsapp.py --dry-run          # só reporta, não escreve
  python3 scripts/backfill_whatsapp.py --pilot <slug>     # roda em 1 artigo
  python3 scripts/backfill_whatsapp.py                    # rollout completo

Hard-fail (exit 1) se restar qualquer ocorrência do número antigo em artigos/.
"""

import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent

OLD = "https://wa.me/5511934329769?text="
NEW = "https://wa.me/5511910932154?text="
OLD_NUM = "5511934329769"


def main():
    dry_run = "--dry-run" in sys.argv
    pilot = None
    if "--pilot" in sys.argv:
        try:
            pilot = sys.argv[sys.argv.index("--pilot") + 1]
        except IndexError:
            sys.exit("[erro] --pilot exige o nome (ou trecho) do arquivo do artigo")

    print("=" * 60)
    modo = "DRY-RUN" if dry_run else (f"PILOTO ({pilot})" if pilot else "ROLLOUT")
    print(f"BACKFILL WHATSAPP — {modo}")

    alvos = sorted((WT / "artigos").glob("*.html"))
    if pilot:
        alvos = [p for p in alvos if pilot in p.name]
        if len(alvos) != 1:
            sys.exit(f"[erro] --pilot '{pilot}' casou com {len(alvos)} arquivos (esperado 1)")

    c = {"trocados": 0, "ja_ok": 0, "sem_cta": []}
    for p in alvos:
        txt = p.read_text(encoding="utf-8")
        if OLD in txt:
            if not dry_run:
                p.write_text(txt.replace(OLD, NEW), encoding="utf-8")
            c["trocados"] += 1
        elif NEW in txt:
            c["ja_ok"] += 1
        else:
            c["sem_cta"].append(p.name)
    print(f"[backfill] trocados: {c['trocados']} | já com número novo: {c['ja_ok']} | sem CTA: {len(c['sem_cta'])}")
    if c["sem_cta"]:
        print(f"[aviso] sem CTA wa.me (não tocados): {c['sem_cta'][:10]}")

    # ── Validação ──
    print("-" * 60)
    todos = sorted((WT / "artigos").glob("*.html"))
    restantes = [p.name for p in todos if OLD_NUM in p.read_text(encoding="utf-8")]
    com_novo = sum(1 for p in todos if NEW in p.read_text(encoding="utf-8"))
    print("VALIDAÇÃO:")
    print(f"  artigos html:                {len(todos)}")
    print(f"  com número novo (wa.me/...): {com_novo}")
    print(f"  com número ANTIGO restante:  {len(restantes)}  (esperado 0 no rollout)")
    print("=" * 60)
    if restantes and not dry_run and not pilot:
        print(f"[FALHA] número antigo ainda presente em: {restantes[:10]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
