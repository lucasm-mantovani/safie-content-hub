"""
buscar_noticia.py — Pipeline unificado do SAFIE Blog (safie.blog.br)

Modelo ESTRITO (canônico Reforma), parametrizado por NICHO:
  1. Para cada categoria do nicho (config/categorias.json), busca via RSS
     (feeds do nicho em config/fontes.json).
  2. Filtro estrito: o item deve conter PELO MENOS um termo-base do nicho
     (config/busca.json[nicho].termos_base) E TODAS as palavras de ao menos
     uma frase-chave da categoria (palavras_chave).
  3. Últimas 48h; sem repetir histórico (URL 15d / categoria 3d).
  4. Scoring: fontes_autoridade + palavras_tecnicas (bônus) - palavras_politicas
     (penalidade) + recência (config/busca.json[nicho]).
  5. Sem notícia fresca → exit 75 (não publica; sem evergreen).

Uso:
  python3 scripts/buscar_noticia.py --nicho reforma
  python3 scripts/buscar_noticia.py --nicho cripto --categoria tokenizacao
"""

import json
import sys
import argparse
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict

import feedparser
from dotenv import load_dotenv

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE              = Path(__file__).resolve().parent.parent
CONFIG_CATEGORIAS = BASE / "config" / "categorias.json"
CONFIG_FONTES     = BASE / "config" / "fontes.json"
CONFIG_BUSCA      = BASE / "config" / "busca.json"
NOTICIA_SAIDA     = BASE / "dados" / "noticia_selecionada.json"
HISTORICO         = BASE / "dados" / "historico_noticias.json"
LOG_DIR           = BASE / "logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
hoje = datetime.now().strftime("%Y-%m-%d")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"busca_{hoje}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

load_dotenv(BASE / ".env")
load_dotenv(Path.home() / ".zshrc", override=False)


# ── Helpers ───────────────────────────────────────────────────────────────────

def ler_json(caminho: Path, padrao):
    if caminho.exists():
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Erro ao ler {caminho}: {e}")
    return padrao


def salvar_json(caminho: Path, dados):
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Histórico (dedup por URL 15d / categoria 3d — decisão #004) ────────────────

def ja_publicado(url: str, tema_slug: str, dias_url: int = 15, dias_tema: int = 3) -> bool:
    dados = ler_json(HISTORICO, {"noticias": []})
    agora = datetime.now(timezone.utc)
    limite_url = agora - timedelta(days=dias_url)
    limite_tema = agora - timedelta(days=dias_tema)
    for item in dados.get("noticias", []):
        item_url = item.get("url_fonte", "")
        item_tema = item.get("tema_slug", "")
        try:
            data_pub = datetime.fromisoformat(item.get("data_publicacao", ""))
        except (ValueError, TypeError):
            continue
        if url and item_url == url and data_pub >= limite_url:
            return True
        if tema_slug and item_tema == tema_slug and data_pub >= limite_tema:
            return True
    return False


def registrar_noticia_publicada(noticia: dict):
    dados = ler_json(HISTORICO, {"noticias": []})
    dados["noticias"].append({
        "data_publicacao": datetime.now(timezone.utc).isoformat(),
        "titulo_noticia": noticia.get("titulo", ""),
        "url_fonte": noticia.get("url", ""),
        "tema_slug": noticia.get("tema_slug", ""),
    })
    dados["noticias"] = dados["noticias"][-90:]
    salvar_json(HISTORICO, dados)


# ── RSS (filtro estrito: termos-base do nicho + frase-chave completa) ──────────

def buscar_rss(categoria: Dict, fontes: List[Dict], termos_base: List[str]) -> List[Dict]:
    """Filtra itens das últimas 48h que contenham (a) pelo menos um termo-base
    do nicho E (b) todas as palavras de ao menos uma frase-chave da categoria."""
    termos_base = [t.lower() for t in termos_base]
    limite = datetime.now(timezone.utc) - timedelta(hours=48)
    resultados = []

    for fonte in fontes:
        log.info(f"[RSS] Lendo {fonte['nome']}...")
        try:
            feed = feedparser.parse(fonte["url"])
            for entry in feed.entries:
                texto = ((entry.get("title") or "") + " " + (entry.get("summary") or "")).lower()

                # (a) gate de nicho: termo-base obrigatório (se lista vazia, não gateia)
                if termos_base and not any(t in texto for t in termos_base):
                    continue

                # (b) match estrito: TODAS as palavras de ao menos uma frase-chave
                frase_bateu = False
                for frase in categoria.get("palavras_chave", []):
                    palavras_frase = [p for p in frase.lower().split() if len(p) >= 4]
                    if palavras_frase and all(p in texto for p in palavras_frase):
                        frase_bateu = True
                        break
                if not frase_bateu:
                    continue

                data_entry = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    ts = time.mktime(entry.published_parsed)
                    data_entry = datetime.fromtimestamp(ts, tz=timezone.utc)
                if data_entry and data_entry < limite:
                    continue

                resultados.append({
                    "titulo": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "fonte": fonte["nome"],
                    "data": data_entry.isoformat() if data_entry else "",
                    "resumo": entry.get("summary", "")[:300],
                    "tema_slug": categoria["slug"],
                    "tema_nome": categoria["nome"],
                    "origem": "rss",
                })
        except Exception as e:
            log.warning(f"[RSS] Erro em {fonte['nome']}: {e}")

    log.info(f"[RSS] {len(resultados)} resultado(s) para categoria '{categoria['nome']}'")
    return resultados


# ── Pontuação (padrão Reforma, termos por nicho) ───────────────────────────────

def pontuar_noticia(noticia: dict, busca_nicho: dict) -> float:
    texto = (noticia.get("titulo", "") + " " + noticia.get("resumo", "")).lower()
    url = noticia.get("url", "").lower()
    fonte = noticia.get("fonte", "").lower()
    pontos = 0.0

    for dominio, score in (busca_nicho.get("fontes_autoridade") or {}).items():
        if dominio in url or dominio in fonte:
            pontos += score
            break

    for palavra in (busca_nicho.get("palavras_tecnicas") or []):
        if palavra.lower() in texto:
            pontos += 3
    for palavra in (busca_nicho.get("palavras_politicas") or []):
        if palavra.lower() in texto:
            pontos -= 4

    data_str = noticia.get("data", "")
    if data_str:
        try:
            data = datetime.fromisoformat(data_str)
            if data.tzinfo is None:
                data = data.replace(tzinfo=timezone.utc)
            horas = (datetime.now(timezone.utc) - data).total_seconds() / 3600
            if horas < 6:
                pontos += 8
            elif horas < 24:
                pontos += 4
        except Exception:
            pass

    if not noticia.get("resumo"):
        pontos -= 3
    return pontos


def selecionar_melhor(candidatos: List[Dict], busca_nicho: dict) -> Optional[Dict]:
    validos = [c for c in candidatos
               if c.get("url") and not ja_publicado(c["url"], c.get("tema_slug", ""))]
    if not validos:
        return None
    validos.sort(key=lambda c: pontuar_noticia(c, busca_nicho), reverse=True)
    escolhida = validos[0]
    log.info(f"Notícia selecionada: [{escolhida['tema_nome']}] {escolhida['titulo']}")
    return escolhida


# ── Orquestrador ────────────────────────────────────────────────────────────

def main(nicho: str, apenas_categoria: str = "") -> Dict:
    log.info("=" * 60)
    log.info(f"BUSCAR NOTÍCIA — início (nicho {nicho})")

    # Higiene: limpar saída anterior (evita consumo ambíguo pelo gerar_artigo)
    if NOTICIA_SAIDA.exists():
        NOTICIA_SAIDA.unlink()

    categorias  = ler_json(CONFIG_CATEGORIAS, [])
    fontes_cfg  = ler_json(CONFIG_FONTES, {"nichos": {}})
    busca_cfg   = ler_json(CONFIG_BUSCA, {"nichos": {}})

    cats_nicho  = [c for c in categorias if c.get("nicho") == nicho]
    if apenas_categoria:
        cats_nicho = [c for c in cats_nicho if c.get("slug") == apenas_categoria]
    if not cats_nicho:
        log.error(f"Nenhuma categoria para nicho '{nicho}'"
                  f"{f' / categoria {apenas_categoria}' if apenas_categoria else ''}")
        sys.exit(1)

    feeds       = fontes_cfg.get("nichos", {}).get(nicho, {}).get("rss_feeds", [])
    busca_nicho = busca_cfg.get("nichos", {}).get(nicho, {})
    termos_base = busca_nicho.get("termos_base", [])
    if not feeds:
        log.error(f"Sem feeds RSS para nicho '{nicho}' em config/fontes.json")
        sys.exit(1)

    todos = []
    for categoria in cats_nicho:
        todos.extend(buscar_rss(categoria, feeds, termos_base))

    noticia = selecionar_melhor(todos, busca_nicho)
    if not noticia:
        log.warning(f"Nenhuma notícia nova para nicho '{nicho}'. Encerrando (exit 75).")
        sys.exit(75)

    log.info("=" * 60)
    log.info(f"RESULTADO: [{noticia.get('tema_nome')}] {noticia.get('titulo')} "
             f"({noticia.get('fonte')})")
    salvar_json(NOTICIA_SAIDA, noticia)
    log.info(f"Salvo em {NOTICIA_SAIDA}")

    if noticia.get("url"):
        try:
            registrar_noticia_publicada(noticia)
        except Exception as e:
            log.warning(f"[aviso] falha ao registrar histórico: {e}")

    return noticia


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Busca notícia do nicho (pipeline unificado)")
    parser.add_argument("--nicho", required=True, help="Nicho: cripto|ecommerce|fintechs|ia|reforma")
    parser.add_argument("--categoria", default="", help="Restringe a uma categoria (slug)")
    args = parser.parse_args()
    main(nicho=args.nicho, apenas_categoria=args.categoria)
