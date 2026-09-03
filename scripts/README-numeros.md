# Dados institucionais do blog (WhatsApp, e-mail, redes) — procedimento de troca

Última troca de número: 03/09/2026 (histórico completo das fases na nota
`content-hub-safie` e na decisão #050/#053 do vault Cerebro).

**Antes de trocar qualquer dado institucional, cumprir a regra de governança do
`CLAUDE.md` deste repo**: consultar o histórico do dado no Cerebro, confirmar o valor
com o Lucas (dono do dado) e registrar a alteração com data, sem apagar o histórico.
Se o vault contradiz o valor pedido, parar e perguntar. Os dois incidentes de número
errado (19/08 e 03/09/2026) foram insumo errado, não execução errada — nenhum
procedimento técnico abaixo protege contra isso.

## Fonte única: `config/site.json` → bloco `institucional`

```json
"institucional": {
  "whatsapp": "55DDNNNNNNNNN",            // só dígitos, com DDI
  "whatsapp_texto": "Olá! Vim pelo blog…", // mensagem pré-preenchida do wa.me
  "email_contato": "contato@safie.com.br",  // espelho da chave legada de topo email_contato
  "same_as": ["https://www.instagram.com/…", "…"]  // JSON-LD Organization.sameAs
}
```

`scripts/sincronizar_institucional.py` propaga esse bloco para os **pontos-fonte**
(templates/ e assets/) e detecta divergência. Ele é o que faz do `site.json` uma
fonte de verdade real: o valor é consumido, não apenas anotado.

### Por que isto mudou (a versão anterior deste README dizia "não criar campo no site.json")

Em 19/08/2026 a regra era: `config/site.json` não é injetado nos templates em build,
logo um campo lá seria **falsa fonte de verdade** (alguém atualiza o campo, nada muda
em produção — decisão #046 do Cerebro). A objeção era correta enquanto não havia
propagação. Desde 03/09/2026 existe propagação explícita e checagem de divergência
(`--check` roda como pré-voo do `rodar_diario.sh` a cada publicação). O campo passou a
ser consumido de fato, então deixou de ser falsa fonte. Não é injeção em build nem
leitura em runtime no navegador: é sincronização de código-fonte, versionada no git.

## Pontos-fonte cobertos pelo sincronizador (não editar à mão)

| Arquivo | O quê |
|---|---|
| `templates/artigo.html` | link `wa.me` + texto do CTA "Falar com a SAFIE" |
| `assets/js/widget-whatsapp.js` | `const WHATSAPP_URL` (número + texto) e o comentário da linha 4 |
| `assets/js/consent.js` | `CFG.whatsapp` — fallback do formulário do banner de consentimento |
| `templates/partials/footer.html` | e-mail (mailto + texto, 2×) |
| `index.html`, `busca.html` | e-mail do rodapé (páginas estáticas não regeneradas pelo pipeline) |
| `templates/home.html`, `index.html` | JSON-LD `Organization.sameAs` |
| `scripts/gerar_artigo.py` | `_PUBLISHER_SAMEAS` (JSON-LD `publisher.sameAs` dos artigos) |

Se um desses arquivos mudar de forma e o padrão não casar mais, o script devolve
`[NAO-RECONHECIDO]` e **não escreve nada** — atualizar o padrão em `pontos()` antes.

Fora do sincronizador de propósito: links pessoais dos sócios (`templates/artigo.html`
"Sobre os autores", `_AUTOR_SAMEAS` em `gerar_artigo.py`) — não são dado institucional.

## Procedimento

```
# 0. Governança (acima). Backup automático: o script cria .bkp datado de cada arquivo que alterar.

# 1. Editar config/site.json → institucional.whatsapp (e/ou email_contato, same_as).
#    Se mudar o e-mail, mudar TAMBÉM a chave legada de topo email_contato (o script exige espelho).

# 2. Propagar para os pontos-fonte
python3 scripts/sincronizar_institucional.py --dry-run   # ver o que muda
python3 scripts/sincronizar_institucional.py             # escrever (idempotente)

# 3. Backfill dos artigos já publicados (irredutível, ver abaixo)
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN --dry-run   # contagens
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN --pilot <slug>  # piloto
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN             # rollout (hard-fail se sobrar antigo)

# 4. Fechamento: tem de sair [OK] Tudo em sincronia… com exit 0
python3 scripts/sincronizar_institucional.py --check
```

`artigos/index.html` não tem CTA (esperado: total de artigos − 1 trocados no backfill).

### Por que o backfill continua existindo

Os artigos (`artigos/*.html`) e as páginas de categoria (`categorias/*.html`) são
**HTML pré-gerado**: cada um carrega o CTA e o rodapé "assados" no arquivo, e é assim
que o Google indexa e que a página funciona sem JavaScript. Trocar o CTA para
renderizar no cliente eliminaria o backfill, mas perderia a indexação do link e
quebraria sem JS — descartado. Logo, toda troca tem duas pernas: sincronizador
(pontos-fonte, valem para artigos novos) **e** backfill (artigos já publicados).
O `--check` conta ocorrências de `wa.me`/`mailto` divergentes em `artigos/` e
`categorias/` e reporta como "backfill pendente", para a segunda perna não ficar
esquecida. Hoje o backfill cobre só o número de WhatsApp; troca de e-mail ou de
`sameAs` em páginas já publicadas ainda precisa de backfill próprio (pendência).

## Pré-voo automático

`rodar_diario.sh` roda `sincronizar_institucional.py --check` no início de cada
publicação. Divergência gera, no log do dia, uma linha com prefixo
`[INSTITUCIONAL-DIVERGENTE]` seguida das linhas `[DIVERGENTE]`/`[NAO-RECONHECIDO]`,
e **a publicação segue** (regra da casa: o post do dia sai). Não é bloqueio, é alarme.

## Pontos FORA do repo — troca manual obrigatória

1. **Redirect pós-formulário no HubSpot** — o form do rodapé redireciona para o
   WhatsApp; o número fica na configuração do form no portal, não no repo.
   Portal `50182013`, form `1802e1da-b81b-44ed-9bab-7db51bd9e6b5`.
2. **Sites institucionais** (`Safie-Copy/site`, `src/lib/data.ts`), **Better Tax**,
   **Equity Calculator** e **Books** (`lib/brand.ts` / `src/lib/brand.ts` + env Vercel)
   — repositórios próprios, cada um com sua fonte única.
3. **Materiais de marketing** — bios de Instagram/LinkedIn, assinaturas de e-mail,
   anúncios, PDFs e afins que citem o número.

## Verificação em produção

Depois do deploy, abrir um artigo em produção e clicar no CTA e no widget: o WhatsApp
deve abrir na conversa do número novo com a mensagem pré-preenchida intacta.
