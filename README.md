# Content Hub SAFIE

Hub central da rede de blogs jurídicos e contábeis da SAFIE.
URL: https://safie.blog.br

## Blogs da rede

| Blog | URL |
|---|---|
| SAFIE Cripto | https://cripto.safie.blog.br |
| SAFIE E-commerce | https://ecommerce.safie.blog.br |
| SAFIE Fintechs | https://fintechs.safie.blog.br |
| SAFIE IA for Business | https://ia.safie.blog.br |
| SAFIE Reforma Tributária | https://reformatributaria.safie.blog.br |

## Como rodar localmente

Abra o arquivo `index.html` diretamente no navegador. Não requer servidor.

## Como atualizar os últimos posts (funcionalidade opcional)

```bash
pip install feedparser
python scripts/fetch_posts.py
```

O script lê os sitemaps dos 5 blogs e gera `data/ultimos_posts.json`.
Esse arquivo é lido pelo `index.html` para exibir os posts recentes em cada card.

## Deploy

Hospedado no Cloudflare Pages.
Cada push na branch `main` dispara deploy automático.

## Manutenção

- Para adicionar um novo blog: edite `config/blogs.json` e atualize `index.html`
- Para atualizar textos do hub: edite `index.html` ou `sobre.html`
- Para atualizar estilos: edite `assets/css/style.css`
- NUNCA editar os arquivos dos blogs filhos por aqui
