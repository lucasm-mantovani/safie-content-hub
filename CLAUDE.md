⚠️ ANTES DE QUALQUER OPERAÇÃO: Ler ~/CLAUDE/CONVENCOES.md
Esse documento define regras de isolamento entre projetos do ecossistema.
Modificar arquivo de outro projeto sem confirmação explícita é ERRO grave.

# Content Hub SAFIE — Instruções Permanentes

## O que é este projeto
Hub central da rede de blogs jurídicos e contábeis da SAFIE.
URL final: https://safie.blog.br
Deploy: Cloudflare Pages (repositório GitHub próprio)

## REGRA DE PROTEÇÃO ABSOLUTA
NUNCA modificar, mover ou apagar arquivos dentro das pastas dos 5 blogs:
- ~/CLAUDE/Blog-Cripto
- ~/CLAUDE/Blog-Ecommerce
- ~/CLAUDE/Blog-Fintechs
- ~/CLAUDE/Blog-IA-for-Business
- ~/CLAUDE/Blog-Reforma-Tributaria

## Estrutura do projeto
Content-Hub-SAFIE/
├── config/blogs.json          → fonte da verdade: dados dos 5 blogs
├── data/ultimos_posts.json    → gerado pelo script Python (opcional)
├── assets/css/                → estilos
├── assets/js/                 → scripts do frontend
├── scripts/                   → scripts Python (RSS, cron)
├── index.html                 → página principal do hub
├── sobre.html                 → página sobre a SAFIE
├── sitemap.xml                → sitemap do hub + links para sitemaps filhos
└── robots.txt                 → permite indexação total

## Blogs da rede
| Blog                    | URL                                    |
|-------------------------|----------------------------------------|
| SAFIE Cripto            | https://cripto.safie.blog.br           |
| SAFIE E-commerce        | https://ecommerce.safie.blog.br        |
| SAFIE Fintechs          | https://fintechs.safie.blog.br         |
| SAFIE IA for Business   | https://ia.safie.blog.br               |
| SAFIE Reforma Tributária| https://reformatributaria.safie.blog.br|

## Identidade visual
Extraída dos blogs filhos na Fase 2. Tokens salvos em assets/css/tokens.css.

## Cron jobs
- scripts/fetch_posts.py → roda às 9h via GitHub Actions, gera data/ultimos_posts.json

## Contatos e links institucionais
- Site: https://safie.com.br
- Email: contato@safie.com.br
- WhatsApp: +55 11 95593-7070 (`wa.me/5511955937070`, vigente desde 03/09/2026; histórico das trocas no git log de `templates/artigo.html`). Hardcoded de propósito em `templates/artigo.html`, `assets/js/widget-whatsapp.js` e `assets/js/consent.js` — trocar sempre pelo procedimento `scripts/README-numeros.md` (fontes + `backfill_whatsapp.py`). Não criar campo em `config/site.json`.
- Copyright: SAFIE Sociedade de Advogados

## Repositório e deploy
- GitHub: https://github.com/lucasm-mantovani/safie-content-hub
- Cloudflare Pages: https://safie-content-hub.pages.dev/
- Domínio: www.safie.blog.br (DNS propagado em 2026-04-28)

## Estado do projeto (atualizado em 2026-04-28)
- [x] Fase 1 — Setup
- [x] Fase 2 — Identidade visual
- [x] Fase 3 — HTML/SEO/GEO
- [x] Fase 4 — fetch_posts.py + GitHub Actions (roda às 9h, gera ultimos_posts.json com 15 posts)
- [x] Fase 5 — GitHub + Cloudflare Pages
- [x] Fase 5 DNS — www.safie.blog.br propagado ✅
- [x] Fase 6 — Validação SEO concluída (2026-04-28): DNS confirmado, HTTP 200, robots.txt + sitemap ok, 15 posts dos 5 blogs no ar

## Decisões do Lucas — registradas em 02/09/2026, não reabrir sem ele

1. **Entidade que publica o blog: a SAFIE**, independentemente de a página tratar de
   Consultoria/Jurídico ou de Contabilidade. O rodapé identifica **SAFIE TECNOLOGIA E
   CONSULTORIA LTDA, CNPJ 42.224.278/0001-92** e fica assim, mesmo sendo uma entidade
   diferente das duas que assinam os sites novos (`Safie-Copy/site/targets/*`).
   Decisão tomada. Nenhuma sessão deve "corrigir" razão social ou CNPJ por conta própria.

2. **Autoria nominal dos artigos.** Os artigos seguem assinados pelos sócios (byline,
   `<meta name="author">` e JSON-LD `author` Person, Lucas Mantovani e Ítalo Cunha),
   com o objetivo declarado de gerar autoridade para os nomes dos sócios, **sem revisão
   artigo por artigo**. É **decisão do Lucas, não recomendação técnica**: o risco
   (conteúdo gerado por IA assinado nominalmente, sem revisão individual) é conhecido e
   assumido por ele. Não alterar autoria nem JSON-LD de autor sem direcionamento explícito.
   Autor definido por regra determinística por nicho (`_AUTOR_POR_NICHO` em
   `gerar_artigo.py`): reforma e ecommerce → Ítalo; cripto, fintechs e ia → Lucas.

3. **Citações atribuídas a sócio saíram (02/09/2026).** O blockquote "citacao-socio" com
   `<cite>` (nome + número de OAB) não é mais gerado nem existe nos artigos publicados.
   A assinatura continua; o que saiu é a afirmação de que um sócio DISSE aquelas palavras.
   Textos impessoais viraram parágrafo de destaque (`p.destaque-artigo`) palavra por
   palavra; textos em primeira pessoa foram removidos. Não reintroduzir citação, `<cite>`
   nem número de OAB em página de conteúdo.

## Copy — vetos vigentes (02/09/2026)

- Nenhuma copy nova sem aprovação. Reaproveitar **verbatim** copy já aprovada dos sites
  (`Safie-Copy/site/targets/{juridico,contabil}/config.ts`).
- Removidos de todas as páginas e proibidos de voltar: "acesso direto aos sócios"
  (afirmação não verdadeira), "jurídico e contabilidade sob o mesmo teto" / "mesma casa"
  (enquadramento de oferta integrada, risco de venda casada) e "nova economia" (saturação).
- Sem travessão longo (—) na copy comercial (rodapé, CTAs, formulário).
- Tagline do rodapé: "Assessoria jurídica e contabilidade para empresas digitais."
  (junção literal das taglines dos dois sites).

## Capa do artigo — rede de proteção (norma permanente, 02/09/2026)

- `gerar_imagem_capa` (`scripts/publicar.py`) **nunca levanta exceção e nunca devolve
  caminho para arquivo que não existe** (existência real + tamanho > 0, não o código de
  retorno do rasterizador). Falha de capa **nunca aborta a publicação**: o post sai.
- Caminho feliz: `<img>` visível, `og:image`, `twitter:image` e `image` do JSON-LD apontam
  para o **mesmo JPG** do artigo (`assets/img/artigos/{slug}.jpg`).
- Se o JPG não existir: o `<img>` usa o **SVG** do artigo (vetorial); `og:image`,
  `twitter:image` e JSON-LD usam a imagem institucional existente
  `assets/img/og-home.jpg` (1200×630). Se ela também faltar, as tags são **omitidas**.
- **`og:image` nunca aponta para SVG** (rede social e JSON-LD não renderizam SVG).
- A capa é **imagem de primeira dobra e candidata a LCP**: o `<img class="artigo-capa">`
  sai com `loading="eager" fetchpriority="high"`, mantendo `width="1200" height="630"`
  (reserva de altura, sem salto de layout). **Nunca `lazy`** — inclusive no fallback SVG.
- O aviso sai em linha própria no log, prefixo `[CAPA-FALLBACK] slug=… motivo=…`.
- Provado em 02/09 com rasterizador levantando exceção e com rasterizador "retornando
  sucesso" sem gravar arquivo: HTML completo, exit 0, aviso no log.
