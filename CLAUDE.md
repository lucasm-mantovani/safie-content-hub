# Content Hub SAFIE — Instruções Permanentes

## O que é este projeto
Hub central da rede de blogs jurídicos e contábeis da SAFIE.
URL final: https://safie.blog.br
Deploy: Cloudflare Pages (repositório GitHub próprio)

## REGRA DE PROTEÇÃO ABSOLUTA
NUNCA modificar, mover ou apagar arquivos dentro das pastas dos 5 blogs:
- ~/CLAUDE/Blog-Cripto
- ~/CLAUDE/Blog-ecommerce
- ~/CLAUDE/Blog-fintechs
- ~/CLAUDE/Blog-ia-for-business
- ~/CLAUDE/Blog-reforma-tributaria

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
- Copyright: SAFIE Sociedade de Advogados

## Repositório e deploy
- GitHub: https://github.com/lucasm-mantovani/safie-content-hub
- Cloudflare Pages: https://safie-content-hub.pages.dev/
- Domínio final: https://safie.blog.br (DNS pendente — pagamento Registro.br)

## Estado do projeto (atualizado em 2026-04-24)
- [x] Fase 1 — Setup
- [x] Fase 2 — Identidade visual
- [x] Fase 3 — HTML/SEO/GEO
- [ ] Fase 4 — RSS opcional (pulada por ora)
- [x] Fase 5 — GitHub + Cloudflare Pages
- [ ] Fase 5 DNS — Apontar safie.blog.br após pagamento no Registro.br
- [ ] Fase 6 — Validação SEO
