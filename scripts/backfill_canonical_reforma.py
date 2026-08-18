"""
backfill_canonical_reforma.py — corrige o host corrompido "reformatributarsafie.blog.br"
nos artigos JÁ PUBLICADOS do nicho reforma (artigos/*.html).

Origem do bug: no migrar.py, o replace de "ia.safie.blog.br"→"safie.blog.br" rodava
antes do de "reformatributaria.safie.blog.br" e casava com o sufixo do host da
reforma, produzindo "reformatributarsafie.blog.br" (host inexistente) em canonical,
og:url e JSON-LD (@id, url, breadcrumb). A fonte foi corrigida no migrar.py (replace
com fronteira); este script cobre apenas os HTMLs baked.

Idempotente: artigo sem a string corrompida não é tocado.

Uso:
  python3 scripts/backfill_canonical_reforma.py --dry-run          # só reporta, não escreve
  python3 scripts/backfill_canonical_reforma.py --pilot <slug>     # roda em 1 artigo
  python3 scripts/backfill_canonical_reforma.py                    # rollout completo

Validações (hard-fail, exit 1):
  - 0 ocorrências de "reformatributarsafie" em artigos/ ao final do rollout
  - todo artigo corrigido fica com canonical self-referencial
    (https://safie.blog.br/artigos/{slug}, pretty, sem .html, sem www)
  - todo bloco <script type="application/ld+json"> dos corrigidos segue parseável
"""

import json
import re
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent

OLD_HOST = "reformatributarsafie.blog.br"
NEW_HOST = "safie.blog.br"

RE_CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')
RE_JSONLD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def validar_artigo(p: Path, txt: str) -> list[str]:
    """Valida um artigo corrigido: canonical self-referencial + JSON-LD parseável."""
    erros = []
    esperado = f"https://{NEW_HOST}/artigos/{p.stem}"
    m = RE_CANONICAL.search(txt)
    if not m:
        erros.append(f"{p.name}: canonical ausente")
    elif m.group(1) != esperado:
        erros.append(f"{p.name}: canonical != esperado ({m.group(1)!r})")
    blocos = RE_JSONLD.findall(txt)
    if not blocos:
        erros.append(f"{p.name}: nenhum bloco JSON-LD encontrado")
    for i, bloco in enumerate(blocos):
        try:
            json.loads(bloco)
        except json.JSONDecodeError as e:
            erros.append(f"{p.name}: JSON-LD #{i+1} não parseia ({e})")
    return erros


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
    print(f"BACKFILL CANONICAL REFORMA — {modo}")

    alvos = sorted((WT / "artigos").glob("*.html"))
    if pilot:
        alvos = [p for p in alvos if pilot in p.name]
        if len(alvos) != 1:
            sys.exit(f"[erro] --pilot '{pilot}' casou com {len(alvos)} arquivos (esperado 1)")

    c = {"corrigidos": 0, "ja_ok": 0}
    erros_validacao = []
    for p in alvos:
        txt = p.read_text(encoding="utf-8")
        if OLD_HOST not in txt:
            c["ja_ok"] += 1
            continue
        novo = txt.replace(OLD_HOST, NEW_HOST)
        erros_validacao += validar_artigo(p, novo)
        if not dry_run:
            p.write_text(novo, encoding="utf-8")
        c["corrigidos"] += 1
    print(f"[backfill] corrigidos: {c['corrigidos']} | sem host corrompido (não tocados): {c['ja_ok']}")

    if erros_validacao:
        print("[FALHA] validação por artigo:")
        for e in erros_validacao[:10]:
            print(f"  - {e}")
        sys.exit(1)

    # ── Validação global ──
    print("-" * 60)
    todos = sorted((WT / "artigos").glob("*.html"))
    restantes = [p.name for p in todos if OLD_HOST in p.read_text(encoding="utf-8")]
    print("VALIDAÇÃO:")
    print(f"  artigos html:                    {len(todos)}")
    print(f"  com host corrompido restante:    {len(restantes)}  (esperado 0 no rollout)")
    print("=" * 60)
    if restantes and not dry_run and not pilot:
        print(f"[FALHA] host corrompido ainda presente em: {restantes[:10]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
