"""
gerar_artigo.py — Pipeline unificado do SAFIE Blog (safie.blog.br)

Gera um artigo completo via Claude API, parametrizado por CATEGORIA.
Base GEO: Blog-reforma-tributaria (canônica). System prompt: factoring do
Blog-ecommerce (construir_system_prompt + chamar_claude de 2 args).

Preserva as 4 camadas GEO:
  C1 — REGRAS_GEO, key_takeaways, citacao_socio, titulos densos, retry+JSON, max_tokens 8000
  C2 — schema author Person + publisher(logo+sameAs) + BreadcrumbList + mainEntityOfPage
  C3 — relacionados (gerado em publicar.py, cross-categoria)
  C4 — llms.txt (gerado em publicar.py)

Citação de sócio: roteada pelo ASSUNTO do artigo (não pelo nicho).

Uso:
  python3 scripts/gerar_artigo.py                 # lê dados/noticia_selecionada.json
  python3 scripts/gerar_artigo.py --dry-run --titulo "..." --categoria "split-payment"
"""

import json
import sys
import re
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE             = Path(__file__).resolve().parent.parent
CONFIG_SITE      = BASE / "config" / "site.json"
CONFIG_CATEGORIAS = BASE / "config" / "categorias.json"
NOTICIA_PATH     = BASE / "dados" / "noticia_selecionada.json"
ARTIGO_PATH      = BASE / "dados" / "artigo_gerado.json"
LOG_DIR          = BASE / "logs"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(exist_ok=True)
hoje = datetime.now().strftime("%Y-%m-%d")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"geracao_{hoje}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

load_dotenv(BASE / ".env")
load_dotenv(Path.home() / ".zshrc", override=False)
# ANTHROPIC_API_KEY — lida de ~/.config/safie/anthropic_key (centralizado, modo 600)
_KEY_PATH = Path.home() / ".config" / "safie" / "anthropic_key"
try:
    ANTHROPIC_API_KEY = _KEY_PATH.read_text().strip()
except FileNotFoundError:
    sys.exit(f"ERRO: chave Anthropic não encontrada em {_KEY_PATH}")
if not ANTHROPIC_API_KEY:
    sys.exit(f"ERRO: chave Anthropic vazia em {_KEY_PATH}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def ler_json(caminho, padrao):
    if Path(caminho).exists():
        try:
            return json.loads(Path(caminho).read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"Erro ao ler {caminho}: {e}")
    return padrao


def salvar_json(caminho, dados):
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def gerar_slug(titulo: str) -> str:
    slug = titulo.lower()
    for orig, rep in [("ã","a"),("â","a"),("á","a"),("à","a"),("ê","e"),("é","e"),
                      ("è","e"),("í","i"),("ì","i"),("ô","o"),("ó","o"),("õ","o"),
                      ("ò","o"),("ú","u"),("ù","u"),("ç","c"),("ñ","n")]:
        slug = slug.replace(orig, rep)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def contar_palavras(texto: str) -> int:
    return len(texto.split())


def estimar_tempo_leitura(texto: str) -> int:
    return max(1, round(contar_palavras(texto) / 200))


def carregar_categoria(cat_slug: str) -> dict:
    """Retorna a entrada de config/categorias.json pelo slug (ou {} se não achar)."""
    cats = ler_json(CONFIG_CATEGORIAS, [])
    return next((c for c in cats if c.get("slug") == cat_slug), {})


# ── System prompt (factoring do ecommerce, parametrizado por categoria) ────────

def construir_system_prompt(config_site: dict, categoria: dict) -> str:
    site_nome = config_site.get("nome", "SAFIE Blog")
    url       = config_site.get("url_completa", "https://safie.blog.br")
    nicho     = categoria.get("nicho", "")
    # Expertise vem da descricao real do nicho (site.json.nichos[nicho].descricao)
    expertise = config_site.get("nichos", {}).get(nicho, {}).get(
        "descricao", "direito e contabilidade para empresas")
    # primeira letra minúscula para fluir em "especialista em {expertise}"
    expertise = expertise[:1].lower() + expertise[1:] if expertise else expertise

    return f"""Você é um especialista em {expertise} no Brasil, escrevendo para o blog {site_nome} ({url}).

Seus artigos seguem o estilo SAFIE: técnico, direto, acessível para empresários e profissionais (não apenas advogados), sem juridiquês excessivo, sem clichês como "no mundo dinâmico" ou "cada vez mais".

Regras obrigatórias:
- Tom institucional, sério, mas compreensível
- Nunca use travessão (—) — use vírgulas, parênteses ou ponto-e-vírgula
- Dados e números concretos sempre que possível
- Citar a fonte original com atribuição clara
- Mínimo 800 palavras, máximo 1.500 palavras no corpo do artigo
- Sempre ancoragem em fato real ou dispositivo normativo específico
- Português brasileiro correto"""


REGRAS_GEO = """REGRAS GEO (otimização para buscadores e IAs generativas) — obrigatórias:

1. FORMATO BLUF (conclusão primeiro): a PRIMEIRA frase do "resumo_executivo" responde
   diretamente à pergunta implícita no título do artigo, sem contexto histórico antes.
   Contexto e ressalvas vêm nas frases seguintes. Errado: "Nos últimos anos, a tributação
   tem mudado...". Certo: "O Imposto Seletivo passa a incidir sobre X a partir de Y, e
   empresas do setor Z precisam se adaptar até W."

2. KEY TAKEAWAYS: o campo "key_takeaways" traz de 3 a 5 fatos-âncora citáveis do artigo.
   Cada item é uma frase autossuficiente contendo dispositivo normativo, prazo, número,
   valor ou entidade. Errado: "É importante entender as mudanças do novo imposto."
   Certo: "A Emenda Constitucional 132/2023 institui o Imposto Seletivo no art. 153,
   VIII, da Constituição Federal."

3. ESTRUTURA DO CORPO (vale para contexto_juridico, impacto_pratico e consideracoes_finais):
   - Cada seção COMEÇA obrigatoriamente com 1 parágrafo <p> de abertura (parágrafo-âncora)
     que resume a seção. NUNCA comece a seção com <h2> ou <h3>.
   - NÃO use <h2> dentro das seções (o título H2 da seção já existe na página).
     Subtítulos internos são sempre <h3>.
   - Subtítulos <h3> densos em entidades: nomeiam a norma, o órgão, o prazo ou as
     categorias tratadas. Certo: "<h3>Faixas de risco do PL 2.338: mínimo, elevado e
     excessivo</h3>". Errado: "<h3>Faixas de risco</h3>".
   - Toda enumeração (passos, categorias, produtos afetados, obrigações, requisitos)
     vai em <ul> ou <ol>. PROIBIDO enumerar em prosa corrida ("primeiramente...,
     em segundo lugar...").
   - Toda comparação entre 2 ou 3 elementos (regime A vs regime B, faixas, antes vs
     depois, mapeamento norma > artigo > obrigação) vai em <table> com <thead> e
     <tbody>. PROIBIDO descrever comparações em prosa.
   - Termos-chave (leis, dispositivos, órgãos, conceitos centrais) em <strong> na
     PRIMEIRA ocorrência no corpo (apenas na primeira).

4. FONTES INLINE: quando um parágrafo afirmar algo com base em fonte externa (notícia,
   órgão, norma publicada online), inclua o link no ponto exato do claim, ex:
   <a href='URL'>segundo o Valor Econômico</a>. Isso vale ALÉM da lista final de
   referências, que continua obrigatória.

5. CITAÇÃO DE SÓCIO: o campo "citacao_socio" traz uma análise em primeira pessoa
   atribuída a um sócio da SAFIE, com 15 a 40 palavras. É leitura de negócio (o que o
   gestor deve pesar na decisão), não promessa de resultado nem autopromoção.
   Escolha o autor pelo ASSUNTO do artigo (NÃO pelo nicho onde ele é publicado):
   "Ítalo Cunha" para temas tributário, fiscal, contábil ou financeiro; "Lucas Mantovani"
   para societário, contratos, LGPD, direito digital ou regulatório. Um artigo tributário
   publicado em qualquer nicho cita Ítalo; um artigo societário cita Lucas.

6. CLAIMS ESPECULATIVOS: se o gancho da notícia depender de tese, anúncio ou alegação
   ainda não verificada (comunicado de empresa, tese não julgada, projeto não votado),
   diga isso explicitamente na primeira menção ("alegação ainda não verificada",
   "tese ainda não pacificada"). A análise jurídica do artigo se sustenta na norma
   vigente; ela NUNCA depende do gancho especulativo.

7. COMPLIANCE OAB (inegociável): sem promessa de resultado, sem comparativo absoluto
   ("o melhor", "o único"), sem captação mercantil. Distinguir sempre o que é norma
   vigente do que é interpretação."""


# ── Prompt de geração ─────────────────────────────────────────────────────────

def montar_prompt(noticia: dict, config_site: dict, categoria: dict) -> str:
    tema_nome    = noticia.get("tema_nome", "") or categoria.get("nome", "")
    titulo_fonte = noticia.get("titulo", "")
    url_fonte    = noticia.get("url", "")
    fonte_nome   = noticia.get("fonte", "")
    resumo_fonte = noticia.get("resumo", "")
    origem       = noticia.get("origem", "rss")
    site_nome    = config_site.get("nome", "SAFIE Blog")
    data_hoje    = datetime.now().strftime("%d/%m/%Y")

    if origem == "evergreen":
        contexto = f"""Este artigo é do tipo evergreen (atemporal). Escreva sobre o tema "{tema_nome}" de forma completa e educativa, com referências aos dispositivos legais vigentes aplicáveis ao tema."""
        referencia = ""
    else:
        contexto = f"""Baseie o artigo na seguinte notícia:

Título da notícia: {titulo_fonte}
Fonte: {fonte_nome}
URL: {url_fonte}
Trecho/resumo: {resumo_fonte[:500] if resumo_fonte else '(sem resumo disponível)'}

Apresente a notícia como ponto de partida e aprofunde a análise dos impactos práticos para empresas."""
        referencia = f"\n- Fonte original: [{fonte_nome}]({url_fonte})" if url_fonte else ""

    return f"""Escreva um artigo completo para o blog {site_nome} sobre o tema "{tema_nome}".

Data de publicação: {data_hoje}

{contexto}

O artigo deve ter EXATAMENTE esta estrutura em JSON (não inclua markdown externo, apenas o JSON):

{{
  "titulo": "(máximo 60 caracteres, com a palavra-chave principal do tema, em português)",
  "meta_description": "(máximo 155 caracteres, resumo atraente para aparecer no Google)",
  "resumo_executivo": "(3 a 4 frases; a PRIMEIRA responde diretamente à pergunta implícita no título, sem contexto antes; sem quebra de linha literal)",
  "key_takeaways": ["(3 a 5 strings; cada uma é um fato-âncora citável: dispositivo normativo, prazo, número, valor ou entidade)"],
  "introducao": "(2 a 3 parágrafos apresentando a notícia ou tema, em HTML com tags <p>)",
  "titulo_contexto": "(H2 da seção jurídica, denso em entidades: nomeie a norma, o órgão ou o prazo tratado, máximo 80 caracteres)",
  "contexto_juridico": "(3 a 4 parágrafos explicando o que isso significa do ponto de vista jurídico e regulatório brasileiro, com referências a leis, artigos e dispositivos específicos, em HTML; comece com <p>; subtítulos internos em <h3>, NUNCA <h2>; use <ul>/<ol>/<table> conforme as REGRAS GEO)",
  "titulo_impacto": "(H2 da seção de impacto prático, denso em entidades, máximo 80 caracteres)",
  "impacto_pratico": "(2 a 3 parágrafos sobre o impacto prático para empresas: o que precisam fazer, adaptar ou monitorar, em HTML com tags <p>)",
  "titulo_consideracoes": "(H2 do fechamento, máximo 80 caracteres)",
  "consideracoes_finais": "(1 a 2 parágrafos de fechamento, em HTML com tags <p>)",
  "citacao_socio": {{"autor": "(Lucas Mantovani OU Ítalo Cunha, escolhido pelo ASSUNTO do artigo)", "texto": "(15 a 40 palavras de análise de negócio, sem promessa de resultado)"}},
  "faq": [
    {{"pergunta": "...", "resposta": "..."}},
    {{"pergunta": "...", "resposta": "..."}},
    {{"pergunta": "...", "resposta": "..."}}
  ],
  "referencias": ["{referencia.strip()}" (inclua a fonte original se houver, e leis ou regulamentos citados)]
}}

Regras:
- O título deve ter no máximo 60 caracteres
- A meta_description deve ter no máximo 155 caracteres
- O FAQ deve ter entre 3 e 5 perguntas reais que empresários ou contadores fariam sobre o tema
- Todo conteúdo em português brasileiro
- Não use travessão (—)
- Parágrafos curtos: máximo 3 linhas. Prefira dividir em 2 parágrafos. Facilita leitura em mobile

{REGRAS_GEO}

- REGRAS CRÍTICAS PARA JSON VÁLIDO:
  - Use aspas simples (') para atributos HTML internos, ex: <a href='...'>, <h2 class='...'>
  - Para aspa dupla literal dentro de uma string, escape com backslash: \\"texto\\"
  - NÃO use quebras de linha literais dentro de strings JSON; use \\n quando necessário
- Retorne APENAS o JSON válido, sem texto antes ou depois"""


# ── Chamada à API do Claude (2 args — factoring ecommerce) ─────────────────────

def chamar_claude(prompt: str, system_prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY não configurada.")
        sys.exit(1)

    log.info("[Claude] Gerando artigo...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )

    resposta = message.content[0].text
    log.info(f"[Claude] Tokens usados — input: {message.usage.input_tokens}, output: {message.usage.output_tokens}")
    return resposta


def salvar_resposta_bruta(texto: str, dir_dados: Path) -> None:
    """Salva resposta bruta do Claude para forense em caso de falha de parsing."""
    try:
        (dir_dados / "ultima_resposta_claude.txt").write_text(texto, encoding="utf-8")
    except Exception as e:
        log.warning(f"[aviso] falha ao salvar resposta bruta: {e}")


# ── Parse da resposta JSON (versão robusta — canônica Reforma) ─────────────────

def extrair_json(texto: str) -> dict:
    """Extrai JSON da resposta do Claude com fallback para sanitização
    de newlines literais dentro de strings. Levanta ValueError se falhar."""
    texto = texto.strip()

    if texto.startswith("```"):
        linhas = texto.split("\n")
        texto = "\n".join(linhas[1:-1])

    inicio = texto.find("{")
    fim    = texto.rfind("}") + 1
    if inicio == -1 or fim == 0:
        raise ValueError("JSON não encontrado na resposta")

    bloco = texto[inicio:fim]

    erro_original = None
    try:
        return json.loads(bloco)
    except json.JSONDecodeError as e1:
        erro_original = str(e1)
        log.warning(f"[fallback] parse direto falhou: {e1}. Sanitizando newlines.")

    try:
        bloco_sanitizado = re.sub(
            r'"(?:[^"\\]|\\.)*"',
            lambda m: m.group(0).replace("\n", " ").replace("\r", " "),
            bloco,
            flags=re.DOTALL
        )
        return json.loads(bloco_sanitizado)
    except json.JSONDecodeError as e2:
        raise ValueError(
            f"JSON inválido após sanitização de newlines. "
            f"Erro original: {erro_original}. Erro pós-sanitização: {e2}"
        ) from e2


# ── Geração com retry (2 args — passa system_prompt) ───────────────────────────

def gerar_artigo_com_retry(prompt_original: str, system_prompt: str, max_tentativas: int = 2) -> dict:
    """Chama o LLM com retry. Se a primeira resposta falhar parse, regenera 1x
    com prompt reforçado. Salva resposta bruta sempre."""
    instrucao_reforco = (
        "\n\nIMPORTANTE: a resposta anterior foi rejeitada por JSON inválido. "
        "Regerar atentando para: (1) usar aspas simples dentro de HTML interno, "
        "ex: <a href='...'>; (2) escapar aspas duplas literais com backslash, "
        "ex: \\\"texto\\\"; (3) NÃO usar quebras de linha literais dentro das "
        "strings JSON, usar \\\\n se necessário."
    )
    prompt_atual = prompt_original
    ultima_excecao = None
    for tentativa in range(max_tentativas):
        resposta = chamar_claude(prompt_atual, system_prompt)
        salvar_resposta_bruta(resposta, BASE / "dados")
        try:
            return extrair_json(resposta)
        except ValueError as e:
            ultima_excecao = e
            log.warning(f"Tentativa {tentativa+1}/{max_tentativas} falhou: {e}")
            if tentativa < max_tentativas - 1:
                prompt_atual = prompt_original + instrucao_reforco
    raise ValueError(f"Falha em {max_tentativas} tentativas. Última: {ultima_excecao}")


# ── Constantes GEO (C1/C2) — idênticas às dos 5 blogs ──────────────────────────

_OAB_SOCIOS = {"Lucas Mantovani": "OAB-SP 506.733", "Ítalo Cunha": "OAB-SP 418.966"}

_AUTOR_SAMEAS = {
    "Lucas Mantovani": [
        "https://www.linkedin.com/in/lucasm-mantovani/",
        "https://www.instagram.com/lucasm.mantovani/"
    ],
    "Ítalo Cunha": [
        "https://www.linkedin.com/in/italo-cunha-cwb/",
        "https://www.instagram.com/euitalocunha/"
    ]
}
_AUTHOR_DEFAULT = "Ítalo Cunha"
_PUBLISHER_LOGO_URL = "https://consultoria.safie.com.br/wp-content/uploads/2025/11/cropped-2-1-1024x292.webp"
_PUBLISHER_SAMEAS = [
    "https://www.instagram.com/safiegroup/",
    "https://www.instagram.com/safiecontabilidade/"
]

_RE_TABELA_MD = re.compile(
    r"(?:^|\n)((?:\|[^\n]+\|[ \t]*\n)\|[ \t:|-]+\|[ \t]*\n(?:\|[^\n]+\|[ \t]*\n?)+)"
)


def _converter_markdown_tabela_para_html(html_bruto: str) -> str:
    """Rede de proteção: converte tabelas markdown (| a | b |) que o modelo
    tenha emitido apesar do prompt exigir HTML."""
    def _converter(m):
        linhas = [l.strip() for l in m.group(1).strip().split("\n") if l.strip()]
        if len(linhas) < 3:
            return m.group(0)
        celulas = lambda l: [c.strip() for c in l.strip("|").split("|")]
        thead = "<tr>" + "".join(f"<th>{c}</th>" for c in celulas(linhas[0])) + "</tr>"
        tbody = "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in celulas(l)) + "</tr>"
            for l in linhas[2:]
        )
        return f"\n<table><thead>{thead}</thead><tbody>{tbody}</tbody></table>\n"
    return _RE_TABELA_MD.sub(_converter, html_bruto)


def _normalizar_secao(html_secao: str, transicao: str) -> str:
    """Rede de proteção por seção: converte tabela markdown, rebaixa <h2>
    internos para <h3>, garante parágrafo-âncora e envolve tabelas para scroll."""
    secao = _converter_markdown_tabela_para_html((html_secao or "").strip())
    secao = re.sub(r"<(/?)h2(\s[^>]*)?>", r"<\1h3\2>", secao)
    if re.match(r"^\s*<h3", secao):
        secao = f"<p>{transicao}</p>\n" + secao
    secao = re.sub(r"(<table[\s\S]*?</table>)", r'<div class="tabela-wrap">\1</div>', secao)
    return secao


# ── Montagem do artigo (canônica Reforma, parametrizada p/ site único) ─────────

def montar_artigo_completo(dados_claude: dict, noticia: dict, config_site: dict, categoria: dict) -> dict:
    data_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _meses    = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    _now      = datetime.now()
    data_fmt  = f"{_now.day} de {_meses[_now.month - 1]} de {_now.year}"
    ano       = str(_now.year)
    titulo    = dados_claude.get("titulo", noticia.get("titulo", ""))
    slug_data = datetime.now().strftime("%Y-%m-%d")
    slug      = f"{slug_data}-{gerar_slug(titulo)}"
    url_blog  = config_site.get("url_completa", "https://safie.blog.br")
    blog_nome = config_site.get("nome", "SAFIE Blog")
    nicho     = categoria.get("nicho", "")

    def _h2(campo: str, fallback: str) -> str:
        t = (dados_claude.get(campo) or "").strip()
        return t if 10 <= len(t) <= 90 else fallback

    # Key takeaways (C1)
    kt_html = ""
    kts = [t.strip() for t in (dados_claude.get("key_takeaways") or []) if t and t.strip()]
    if len(kts) >= 3:
        kt_html = (
            '<div class="key-takeaways">\n'
            '  <p class="key-takeaways-titulo">Principais pontos</p>\n'
            '  <ul>\n' + "".join(f"    <li>{t}</li>\n" for t in kts[:5]) +
            '  </ul>\n</div>\n\n'
        )

    # Citação de sócio (C1) — whitelist dura de autor
    cit = dados_claude.get("citacao_socio") or {}
    if not isinstance(cit, dict):
        cit = {}
    autor     = (cit.get("autor") or "").strip()
    texto_cit = (cit.get("texto") or "").strip()
    citacao_html = ""
    if autor in _OAB_SOCIOS and 10 <= len(texto_cit.split()) <= 50:
        citacao_html = (
            '\n<blockquote class="citacao-socio">\n'
            f'  <p>{texto_cit}</p>\n'
            f'  <cite>{autor}, sócio da SAFIE ({_OAB_SOCIOS[autor]})</cite>\n'
            '</blockquote>\n'
        )

    corpo_html = (
        kt_html +
        dados_claude.get("introducao", "") +
        f"\n\n<h2>{_h2('titulo_contexto', 'Contexto jurídico e regulatório')}</h2>\n" +
        _normalizar_secao(dados_claude.get("contexto_juridico", ""),
                          "Os fundamentos normativos do tema estão detalhados a seguir.") +
        f"\n\n<h2>{_h2('titulo_impacto', 'Impacto prático para empresas')}</h2>\n" +
        _normalizar_secao(dados_claude.get("impacto_pratico", ""),
                          "Na prática, os efeitos para as empresas são os seguintes.") +
        citacao_html +
        f"\n\n<h2>{_h2('titulo_consideracoes', 'Considerações finais')}</h2>\n" +
        _normalizar_secao(dados_claude.get("consideracoes_finais", ""),
                          "Em síntese, os pontos de atenção são estes.")
    )

    faq_html = ""
    for item in dados_claude.get("faq", []):
        pergunta = item.get("pergunta", "")
        resposta = item.get("resposta", "")
        faq_html += (
            f'<div class="faq-item" itemscope itemtype="https://schema.org/Question">\n'
            f'  <p class="faq-pergunta" itemprop="name">{pergunta}</p>\n'
            f'  <div class="faq-resposta" itemscope itemtype="https://schema.org/Answer">'
            f'<span itemprop="text">{resposta}</span></div>\n'
            f'</div>\n'
        )

    refs = dados_claude.get("referencias", [])
    if noticia.get("url") and noticia.get("fonte"):
        ref_original = f"[{noticia['fonte']}]({noticia['url']})"
        if ref_original not in " ".join(refs):
            refs.insert(0, ref_original)

    refs_html = "<ul>\n"
    for ref in refs:
        if not ref or not ref.strip():
            continue
        ref_text = ref.strip().lstrip("-").strip()
        match = re.search(r"\[(.+?)\]\((.+?)\)", ref_text)
        if match:
            link_text = match.group(1)
            link_url = match.group(2)
            link_html = f'<a href="{link_url}" target="_blank" rel="noopener">{link_text}</a>'
            prefix = ref_text[:match.start()].strip().rstrip(":").strip()
            if prefix:
                refs_html += f'<li><span class="ref-label">{prefix}:</span> {link_html}</li>\n'
            else:
                refs_html += f'<li>{link_html}</li>\n'
        else:
            refs_html += f'<li>{ref_text}</li>\n'
    refs_html += "</ul>\n"

    faq_schema = [
        {
            "@type": "Question",
            "name": item.get("pergunta", ""),
            "acceptedAnswer": {"@type": "Answer", "text": item.get("resposta", "")}
        }
        for item in dados_claude.get("faq", [])
    ]

    # Autor do schema (C2): sócio da citação se válido; senão default
    autor_schema = autor if autor in _OAB_SOCIOS else _AUTHOR_DEFAULT
    tema_nome_s  = noticia.get("tema_nome", "") or categoria.get("nome", "")
    tema_slug_s  = noticia.get("tema_slug", "") or categoria.get("slug", "")

    schema = [
        {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": titulo,
            "description": dados_claude.get("meta_description", ""),
            "datePublished": data_iso,
            "dateModified": data_iso,
            "mainEntityOfPage": {"@type": "WebPage", "@id": f"{url_blog}/artigos/{slug}"},
            "author": {
                "@type": "Person",
                "name": autor_schema,
                "sameAs": _AUTOR_SAMEAS[autor_schema],
            },
            "publisher": {
                "@type": "Organization",
                "name": "SAFIE",
                "url": "https://safie.com.br",
                "logo": {"@type": "ImageObject", "url": _PUBLISHER_LOGO_URL},
                "sameAs": _PUBLISHER_SAMEAS,
            },
            "url": f"{url_blog}/artigos/{slug}",
            "articleSection": tema_nome_s,
            "inLanguage": "pt-BR",
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_schema,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Início", "item": url_blog},
                {"@type": "ListItem", "position": 2, "name": tema_nome_s, "item": f"{url_blog}/categorias/{tema_slug_s}"},
                {"@type": "ListItem", "position": 3, "name": titulo, "item": f"{url_blog}/artigos/{slug}"},
            ],
        },
    ]

    relacionados_html = (
        '<p style="color:var(--cinza);font-size:0.9rem;">Mais artigos em breve.</p>'
    )

    return {
        "slug": slug,
        "titulo": titulo,
        "meta_titulo": f"{titulo} — {blog_nome}",
        "meta_description": dados_claude.get("meta_description", ""),
        "canonical_url": f"{url_blog}/artigos/{slug}",
        "data_iso": data_iso,
        "data_formatada": data_fmt,
        "ano": ano,
        "tempo_leitura": estimar_tempo_leitura(corpo_html),
        "tema_nome": tema_nome_s,
        "tema_slug": tema_slug_s,
        "nicho": nicho,
        "resumo_executivo": dados_claude.get("resumo_executivo", ""),
        "conteudo": corpo_html,
        "faq_html": faq_html,
        "referencias_html": refs_html,
        "relacionados_html": relacionados_html,
        "schema_json": json.dumps(schema, ensure_ascii=False, indent=2),
        "palavras_corpo": contar_palavras(corpo_html),
        "noticia_origem": noticia,
    }


# ── Relatório de dry-run ──────────────────────────────────────────────────────

def _relatorio_dry_run(artigo: dict, dados_claude: dict) -> None:
    corpo = artigo["conteudo"]
    cit = dados_claude.get("citacao_socio") or {}
    if not isinstance(cit, dict):
        cit = {}
    kts = dados_claude.get("key_takeaways") or []
    print("\n── RELATÓRIO DRY-RUN ──")
    print(f"Nicho / categoria: {artigo.get('nicho')} / {artigo.get('tema_slug')}")
    print(f"Listas no corpo (ul/ol): {corpo.count('<ul')}/{corpo.count('<ol')}")
    print(f"Tabelas: {corpo.count('<table')}")
    print(f"<strong>: {corpo.count('<strong>')}")
    print(f"Links inline no corpo: {corpo.count('<a ')}")
    h2_vazio = bool(re.search(r"<h2[^>]*>[^<]*</h2>\s*<h[23]", corpo))
    print(f"H2 vazio: {'SIM' if h2_vazio else 'não'}")
    print(f"key_takeaways: {len(kts)} itens")
    print(f"citacao_socio: {cit.get('autor', 'AUSENTE')} ({len((cit.get('texto') or '').split())} palavras)")
    print(f"resumo_executivo: {len(str(artigo.get('resumo_executivo', '')).split())} palavras")
    print(f"Palavras no corpo: {artigo['palavras_corpo']}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(noticia_path: Path = NOTICIA_PATH, dry_run: bool = False,
         titulo_teste: str = None, categoria_slug: str = None) -> dict:
    log.info("=" * 60)
    log.info(f"GERAR ARTIGO — início{' [DRY-RUN]' if dry_run else ''}")

    config_site = ler_json(CONFIG_SITE, {})

    if titulo_teste:
        categoria = carregar_categoria(categoria_slug or "")
        noticia = {
            "titulo": titulo_teste,
            "tema_nome": categoria.get("nome", categoria_slug or ""),
            "tema_slug": categoria.get("slug", categoria_slug or ""),
            "origem": "evergreen",
            "url": "", "fonte": "", "resumo": "",
        }
    else:
        noticia = ler_json(noticia_path, {})
        categoria = carregar_categoria(noticia.get("tema_slug", ""))

    if not noticia:
        log.error(f"Nenhuma notícia encontrada em {noticia_path}")
        sys.exit(1)
    if not categoria:
        log.error(f"Categoria '{categoria_slug or noticia.get('tema_slug')}' não encontrada em categorias.json")
        sys.exit(1)

    log.info(f"Notícia: {noticia.get('titulo', '(sem título)')}")
    log.info(f"Categoria: {categoria.get('nome')} (nicho {categoria.get('nicho')})")

    system_prompt = construir_system_prompt(config_site, categoria)
    prompt        = montar_prompt(noticia, config_site, categoria)
    dados_claude  = gerar_artigo_com_retry(prompt, system_prompt)

    artigo = montar_artigo_completo(dados_claude, noticia, config_site, categoria)

    log.info(f"Artigo gerado: '{artigo['titulo']}' ({artigo['palavras_corpo']} palavras)")
    log.info(f"Slug: {artigo['slug']}")

    if dry_run:
        destino = BASE / "dados" / f"artigo_dry_run_{datetime.now():%Y%m%d_%H%M}.json"
        salvar_json(destino, artigo)
        log.info(f"[DRY-RUN] Artigo salvo em {destino} (artigo_gerado.json intacto; publicar.py NÃO acionado)")
        _relatorio_dry_run(artigo, dados_claude)
    else:
        salvar_json(ARTIGO_PATH, artigo)
        log.info(f"Artigo salvo em {ARTIGO_PATH}")
    log.info("=" * 60)

    return artigo


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera artigo via Claude API (pipeline unificado)")
    parser.add_argument("--noticia", default=str(NOTICIA_PATH), help="Caminho para o JSON da notícia")
    parser.add_argument("--dry-run", action="store_true", help="Gera sem gravar artigo_gerado.json (não publica)")
    parser.add_argument("--titulo", default=None, help="Título de teste (dispensa noticia_selecionada.json)")
    parser.add_argument("--categoria", default=None, help="Slug da categoria (ex.: split-payment)")
    args = parser.parse_args()

    artigo = main(noticia_path=Path(args.noticia), dry_run=args.dry_run,
                  titulo_teste=args.titulo, categoria_slug=args.categoria)
    print(f"\nArtigo gerado: {artigo['titulo']}")
    print(f"Palavras: {artigo['palavras_corpo']}")
    print(f"Slug: {artigo['slug']}")
