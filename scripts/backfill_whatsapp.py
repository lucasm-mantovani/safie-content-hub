"""
backfill_whatsapp.py — troca o número de WhatsApp da SAFIE na URL wa.me do CTA
"Falar com a SAFIE" nos artigos JÁ PUBLICADOS (artigos/*.html).

A fonte (templates/artigo.html e assets/js/widget-whatsapp.js) é trocada à parte;
este script cobre apenas os HTMLs baked. Idempotente: artigo já com o número novo
(ou sem CTA, como artigos/index.html) não é tocado.

Uso:
  python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN --dry-run
  python3 scripts/backfill_whatsapp.py --old ... --new ... --pilot <slug>   # roda em 1 artigo
  python3 scripts/backfill_whatsapp.py --old ... --new ...                  # rollout completo

Hard-fail (exit 1) se restar qualquer ocorrência do número antigo em artigos/.
"""

import argparse
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent


def parse_args():
    ap = argparse.ArgumentParser(description="Troca o número de WhatsApp nos artigos publicados (artigos/*.html).")
    ap.add_argument("--old", required=True, help="número antigo: 55 + DDD + número, apenas dígitos")
    ap.add_argument("--new", required=True, help="número novo: 55 + DDD + número, apenas dígitos")
    ap.add_argument("--dry-run", action="store_true", help="só reporta, não escreve")
    ap.add_argument("--pilot", metavar="SLUG", help="roda em 1 artigo (nome ou trecho do arquivo)")
    args = ap.parse_args()
    for label, num in (("--old", args.old), ("--new", args.new)):
        if not num.isdigit() or not (12 <= len(num) <= 13):
            ap.error(f"{label} deve ser só dígitos com DDI 55 (12-13 dígitos), recebido: {num!r}")
    if args.old == args.new:
        ap.error("--old e --new são iguais")
    return args


def main():
    args = parse_args()
    old_url = f"https://wa.me/{args.old}?text="
    new_url = f"https://wa.me/{args.new}?text="

    print("=" * 60)
    modo = "DRY-RUN" if args.dry_run else (f"PILOTO ({args.pilot})" if args.pilot else "ROLLOUT")
    print(f"BACKFILL WHATSAPP — {modo}")
    print(f"  old: {args.old}  ->  new: {args.new}")

    alvos = sorted((WT / "artigos").glob("*.html"))
    if args.pilot:
        alvos = [p for p in alvos if args.pilot in p.name]
        if len(alvos) != 1:
            sys.exit(f"[erro] --pilot '{args.pilot}' casou com {len(alvos)} arquivos (esperado 1)")

    c = {"trocados": 0, "ocorrencias": 0, "ja_ok": 0, "sem_cta": []}
    for p in alvos:
        txt = p.read_text(encoding="utf-8")
        if old_url in txt:
            if not args.dry_run:
                p.write_text(txt.replace(old_url, new_url), encoding="utf-8")
            c["trocados"] += 1
            c["ocorrencias"] += txt.count(old_url)
        elif new_url in txt:
            c["ja_ok"] += 1
        else:
            c["sem_cta"].append(p.name)
    print(f"[backfill] trocados: {c['trocados']} ({c['ocorrencias']} ocorrências) | já com número novo: {c['ja_ok']} | sem CTA: {len(c['sem_cta'])}")
    if c["sem_cta"]:
        print(f"[aviso] sem CTA wa.me (não tocados): {c['sem_cta'][:10]}")

    # ── Validação ──
    print("-" * 60)
    todos = sorted((WT / "artigos").glob("*.html"))
    restantes = [p.name for p in todos if args.old in p.read_text(encoding="utf-8")]
    com_novo = sum(1 for p in todos if new_url in p.read_text(encoding="utf-8"))
    print("VALIDAÇÃO:")
    print(f"  artigos html:                {len(todos)}")
    print(f"  com número novo (wa.me/...): {com_novo}")
    print(f"  com número ANTIGO restante:  {len(restantes)}  (esperado 0 no rollout)")
    print("=" * 60)
    if restantes and not args.dry_run and not args.pilot:
        print(f"[FALHA] número antigo ainda presente em: {restantes[:10]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
