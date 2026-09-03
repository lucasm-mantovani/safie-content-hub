#!/usr/bin/env python3
"""
sincronizar_institucional.py — propaga os dados institucionais de config/site.json
(bloco "institucional") para os pontos-fonte hardcoded do repositório e detecta
divergência entre eles. É o que torna o site.json fonte única de verdade de fato,
e não um campo solto (decisão #046 do Cerebro: campo não consumido é falsa fonte).

Modos:
  (padrão)   escreve nos pontos-fonte o valor do site.json (idempotente; cria
             .bkp datado antes de alterar cada arquivo)
  --dry-run  mostra o que mudaria; não escreve
  --check    não escreve; exit 1 se houver divergência ou ponto não reconhecido.
             É o pré-voo do rodar_diario.sh (avisa e segue publicando).

O que NÃO faz: não toca artigos/*.html nem categorias/*.html. São páginas
pré-geradas (HTML estático, indexado, funciona sem JS) — a troca lá é o backfill
(scripts/backfill_whatsapp.py, ver scripts/README-numeros.md). Em --check, porém,
conta ocorrências de wa.me / mailto divergentes nessas pastas e reporta como
"backfill pendente", para a divergência não ficar silenciosa.

Sem rede, sem leitura em runtime no navegador, sem mudança no HTML publicado
além do que o operador mandar propagar.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

BASE = Path(__file__).resolve().parent.parent
SITE = BASE / "config" / "site.json"

# Prefixos de saída (linha própria, grep-áveis no log do pipeline)
OK, DIV, NR, UPD = "[OK]", "[DIVERGENTE]", "[NAO-RECONHECIDO]", "[ATUALIZADO]"


def carregar_institucional():
    site = json.loads(SITE.read_text(encoding="utf-8"))
    inst = site.get("institucional")
    if not isinstance(inst, dict):
        sys.exit(f"{NR} config/site.json: bloco 'institucional' ausente")
    w = str(inst.get("whatsapp", ""))
    if not (w.isdigit() and w.startswith("55") and 12 <= len(w) <= 13):
        sys.exit(f"{NR} config/site.json: institucional.whatsapp inválido ({w!r}); "
                 "esperado só dígitos com DDI 55 (12-13 dígitos)")
    texto = inst.get("whatsapp_texto", "")
    if not texto:
        sys.exit(f"{NR} config/site.json: institucional.whatsapp_texto vazio")
    email = inst.get("email_contato", "")
    if "@" not in email:
        sys.exit(f"{NR} config/site.json: institucional.email_contato inválido ({email!r})")
    same_as = inst.get("same_as")
    if not (isinstance(same_as, list) and same_as and all(u.startswith("https://") for u in same_as)):
        sys.exit(f"{NR} config/site.json: institucional.same_as deve ser lista não vazia de URLs https")
    # A chave legada de topo continua existindo; tem de ser espelho do bloco.
    legado = site.get("email_contato")
    if legado is not None and legado != email:
        sys.exit(f"{DIV} config/site.json: email_contato (topo) = {legado!r} difere de "
                 f"institucional.email_contato = {email!r}")
    return {
        "whatsapp": w,
        "texto": texto,
        # Mesma forma que o navegador gera com encodeURIComponent, exceto '!'
        # que os pontos-fonte mantêm literal (Ol%C3%A1!%20Vim...).
        "texto_url": quote(texto, safe="!"),
        "email": email,
        "same_as": list(same_as),
    }


# ── Pontos-fonte ────────────────────────────────────────────────────────────────
# Cada ponto: arquivo, rótulo, regex com grupos nomeados, valores esperados por
# grupo e quantidade exata de ocorrências. Quantidade diferente = arquivo mudou
# de forma e o script NÃO escreve às cegas ([NAO-RECONHECIDO]).

def pontos(v):
    return [
        dict(arquivo="templates/artigo.html", rotulo="CTA 'Falar com a SAFIE' (wa.me + texto)",
             regex=r'href="https://wa\.me/(?P<num>\d+)\?text=(?P<txt>[^"]*)"',
             esperado={"num": v["whatsapp"], "txt": v["texto_url"]}, n=1),
        dict(arquivo="assets/js/widget-whatsapp.js", rotulo="comentário 'Destino: wa.me/…' (linha 4)",
             regex=r'// Destino: wa\.me/(?P<num>\d+) com mensagem',
             esperado={"num": v["whatsapp"]}, n=1),
        dict(arquivo="assets/js/widget-whatsapp.js", rotulo="const WHATSAPP_URL (número + texto)",
             regex=r"const WHATSAPP_URL = 'https://wa\.me/(?P<num>\d+)\?text=' \+ encodeURIComponent\('(?P<txt>[^']*)'\)",
             esperado={"num": v["whatsapp"], "txt": v["texto"]}, n=1),
        dict(arquivo="assets/js/consent.js", rotulo="CFG.whatsapp (fallback do formulário)",
             regex=r"whatsapp: 'https://wa\.me/(?P<num>\d+)\?text=(?P<txt>[^']*)'",
             esperado={"num": v["whatsapp"], "txt": v["texto_url"]}, n=1),
        dict(arquivo="templates/partials/footer.html", rotulo="e-mail (mailto + texto, 2×)",
             regex=r'mailto:(?P<href>[^"]+)">(?P<txt>[^<]+)</a>',
             esperado={"href": v["email"], "txt": v["email"]}, n=2),
        dict(arquivo="index.html", rotulo="e-mail do rodapé (página estática, 2×)",
             regex=r'mailto:(?P<href>[^"]+)">(?P<txt>[^<]+)</a>',
             esperado={"href": v["email"], "txt": v["email"]}, n=2),
        dict(arquivo="busca.html", rotulo="e-mail do rodapé (página estática, 2×)",
             regex=r'mailto:(?P<href>[^"]+)">(?P<txt>[^<]+)</a>',
             esperado={"href": v["email"], "txt": v["email"]}, n=2),
        dict(arquivo="templates/home.html", rotulo="JSON-LD Organization.sameAs",
             regex=r'"sameAs": \[(?P<lista>[^\]]*)\]', lista=v["same_as"], n=1),
        dict(arquivo="index.html", rotulo="JSON-LD Organization.sameAs",
             regex=r'"sameAs": \[(?P<lista>[^\]]*)\]', lista=v["same_as"], n=1),
        dict(arquivo="scripts/gerar_artigo.py", rotulo="_PUBLISHER_SAMEAS (JSON-LD dos artigos)",
             regex=r'_PUBLISHER_SAMEAS = \[(?P<lista>[^\]]*)\]', lista=v["same_as"], n=1),
    ]


def _urls_da_lista(bloco):
    return re.findall(r'"([^"]+)"', bloco)


def _render_lista(bloco_atual, urls):
    """Reescreve a lista preservando a indentação do bloco atual."""
    m_item = re.search(r'\n([ \t]*)"', bloco_atual)
    m_fim = re.search(r'\n([ \t]*)$', bloco_atual)
    ind_item = m_item.group(1) if m_item else "    "
    ind_fim = m_fim.group(1) if m_fim else ""
    return "\n" + ",\n".join(f'{ind_item}"{u}"' for u in urls) + "\n" + ind_fim


def processar(ponto, modo):
    """Devolve (status, mensagem, novo_conteudo|None)."""
    caminho = BASE / ponto["arquivo"]
    if not caminho.exists():
        return NR, f"{ponto['arquivo']}: arquivo não existe", None
    conteudo = caminho.read_text(encoding="utf-8")
    matches = list(re.finditer(ponto["regex"], conteudo))
    if len(matches) != ponto["n"]:
        return NR, (f"{ponto['arquivo']}: {ponto['rotulo']} — esperado {ponto['n']} ocorrência(s), "
                    f"encontrado {len(matches)}"), None

    divergencias = []
    novo = conteudo
    for m in reversed(matches):  # de trás para frente: offsets continuam válidos
        if "lista" in ponto:
            atual = _urls_da_lista(m.group("lista"))
            if atual != ponto["lista"]:
                divergencias.append(f"atual={atual} esperado={ponto['lista']}")
                s, e = m.span("lista")
                novo = novo[:s] + _render_lista(m.group("lista"), ponto["lista"]) + novo[e:]
        else:
            for grupo, esperado in ponto["esperado"].items():
                if m.group(grupo) != esperado:
                    divergencias.append(f"{grupo}: atual={m.group(grupo)!r} esperado={esperado!r}")
            # substitui grupo a grupo, do último para o primeiro
            for grupo in sorted(ponto["esperado"], key=lambda g: m.start(g), reverse=True):
                s, e = m.span(grupo)
                novo = novo[:s] + ponto["esperado"][grupo] + novo[e:]

    if not divergencias:
        return OK, f"{ponto['arquivo']}: {ponto['rotulo']}", None
    return DIV, f"{ponto['arquivo']}: {ponto['rotulo']} — " + "; ".join(divergencias), novo


def checar_paginas_geradas(v):
    """artigos/ e categorias/: só leitura. Divergência aqui = backfill pendente."""
    problemas = []
    for pasta in ("artigos", "categorias"):
        d = BASE / pasta
        if not d.is_dir():
            continue
        nums, mails = {}, {}
        for f in sorted(d.glob("*.html")):
            t = f.read_text(encoding="utf-8", errors="replace")
            for n in re.findall(r"wa\.me/(\d+)", t):
                if n != v["whatsapp"]:
                    nums.setdefault(n, []).append(f.name)
            for e in re.findall(r"mailto:([^\"'?]+)", t):
                if e != v["email"]:
                    mails.setdefault(e, []).append(f.name)
        for n, fs in nums.items():
            problemas.append(f"{pasta}/: wa.me/{n} em {len(fs)} página(s) (vigente {v['whatsapp']}) — "
                             f"backfill pendente, ex.: {fs[0]}")
        for e, fs in mails.items():
            problemas.append(f"{pasta}/: mailto:{e} em {len(fs)} página(s) (vigente {v['email']}) — "
                             f"backfill pendente, ex.: {fs[0]}")
    return problemas


def main():
    ap = argparse.ArgumentParser(description="Propaga/checa os dados institucionais do config/site.json.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="mostra o que mudaria; não escreve")
    g.add_argument("--check", action="store_true", help="não escreve; exit 1 se houver divergência")
    args = ap.parse_args()
    modo = "check" if args.check else ("dry-run" if args.dry_run else "escrever")

    v = carregar_institucional()
    print(f"Fonte: config/site.json → whatsapp={v['whatsapp']} email={v['email']} same_as={len(v['same_as'])} URL(s) [modo {modo}]")

    falhas = 0
    a_escrever = {}  # arquivo -> conteudo (vários pontos podem cair no mesmo arquivo)
    for ponto in pontos(v):
        # Se um ponto anterior já alterou este arquivo, processar sobre a versão nova
        caminho = BASE / ponto["arquivo"]
        original = None
        if ponto["arquivo"] in a_escrever:
            original = caminho.read_text(encoding="utf-8")
            caminho.write_text(a_escrever[ponto["arquivo"]], encoding="utf-8")
        try:
            status, msg, novo = processar(ponto, modo)
        finally:
            if original is not None:
                caminho.write_text(original, encoding="utf-8")
        if status == OK:
            print(f"{OK} {msg}")
        elif status == NR:
            falhas += 1
            print(f"{NR} {msg}")
        else:
            falhas += 1
            print(f"{DIV} {msg}")
            if modo == "escrever":
                a_escrever[ponto["arquivo"]] = novo

    for p in checar_paginas_geradas(v):
        falhas += 1
        print(f"{DIV} {p}")

    if modo == "escrever" and a_escrever:
        hoje = date.today().strftime("%Y%m%d")
        for arq, conteudo in a_escrever.items():
            caminho = BASE / arq
            bkp = caminho.with_name(f"{caminho.name}.bkp.{hoje}-pre-sincronizar-institucional")
            if not bkp.exists():
                shutil.copy2(caminho, bkp)
            caminho.write_text(conteudo, encoding="utf-8")
            print(f"{UPD} {arq} (backup: {bkp.name})")
        print("Pontos-fonte atualizados. Lembrete: artigos/ e categorias/ já publicados precisam do backfill "
              "(scripts/README-numeros.md). Rode --check de novo para confirmar.")
        # Depois de escrever, a divergência dos pontos-fonte foi resolvida; o exit
        # reflete só o que ainda está pendente (páginas geradas / não reconhecidos).
        restantes = sum(1 for p in pontos(v) if processar(p, "check")[0] != OK) + len(checar_paginas_geradas(v))
        sys.exit(1 if restantes else 0)

    if falhas:
        print(f"{DIV} {falhas} divergência(s)/ponto(s) não reconhecido(s). Nada escrito"
              + (" (--check)." if modo == "check" else " (--dry-run)."))
        sys.exit(1)
    print(f"{OK} Tudo em sincronia com config/site.json.")
    sys.exit(0)


if __name__ == "__main__":
    main()
