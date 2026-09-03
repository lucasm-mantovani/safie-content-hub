# Troca do número de WhatsApp da SAFIE — procedimento

Última troca: 03/09/2026 (para o número atual; ver git log de `templates/artigo.html`).
O número é **hardcoded de propósito** — `config/site.json` NÃO é injetado nos
templates em build, então um campo lá seria falsa fonte de verdade. Não criar.

## 1. Pontos-fonte no repo (trocar primeiro, com backup .bkp datado)

| Arquivo | Linha | O quê |
|---|---|---|
| `templates/artigo.html` | 109 | link `wa.me` do CTA "Falar com a SAFIE" |
| `assets/js/widget-whatsapp.js` | 12 | `const WHATSAPP_URL` do widget flutuante |
| `assets/js/widget-whatsapp.js` | 4 | comentário com o número (manter em sincronia) |
| `assets/js/consent.js` | 18 | `CFG.whatsapp` — o fallback do formulário no banner de consentimento (no ar desde 19/08/2026) usa esse valor |

## 2. Backfill dos artigos já publicados (artigos/*.html)

```
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN --dry-run   # 1º: conferir contagens
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN --pilot <slug>  # 2º: piloto em 1 artigo
python3 scripts/backfill_whatsapp.py --old 55DDNNNNNNNNN --new 55DDNNNNNNNNN             # 3º: rollout (hard-fail se sobrar antigo)
```

Argumentos só com dígitos: `55` + DDD + número. `artigos/index.html` não tem CTA
(esperado: total de artigos − 1 trocados). O script é idempotente.

## 3. Pontos FORA do repo — troca manual obrigatória

1. **Redirect pós-formulário no HubSpot** — o form do rodapé redireciona para o
   WhatsApp; o número fica na configuração do form no portal, não no repo.
   Portal `50182013`, form `1802e1da-b81b-44ed-9bab-7db51bd9e6b5`.
2. **Site institucional safie.com.br** — repositório próprio, fora deste repo.
3. **Materiais de marketing** — bios de Instagram/LinkedIn, assinaturas de
   e-mail, anúncios, PDFs e afins que citem o número.

## 4. Checagem de fechamento (antes do commit)

```
grep -rn '<NUMERO_ANTIGO_COM_DDI>' --exclude-dir=.git --exclude='*.bkp.*' .
grep -rn '<NUMERO_ANTIGO_SEM_DDI>' --exclude-dir=.git --exclude='*.bkp.*' .
```

Ambos devem retornar **zero** ocorrências (os `.bkp` são registro histórico e
ficam de fora). Depois do deploy, abrir um artigo em produção e clicar no CTA e
no widget: o WhatsApp deve abrir na conversa do número novo com a mensagem
pré-preenchida intacta ("Olá! Vim pelo blog da SAFIE e gostaria de conversar.").
