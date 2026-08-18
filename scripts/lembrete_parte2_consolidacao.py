"""
lembrete_parte2_consolidacao.py — lembrete de disparo ÚNICO por e-mail para
executar a Parte 2 (consolidação B1 dos 47 clusters de duplicatas do blog).

Agendado pelo LaunchAgent br.safie.blog.lembrete-parte2 (4 janelas em set/2026:
01/09 09:00 e 15:00, 02/09 09:00, 03/09 09:00 — janelas extras são retry em
caso de falha de SMTP; o flag abaixo garante que o e-mail sai UMA vez só).

Idempotência / auto-desabilite:
  - Flag ~/.config/safie/lembrete_parte2_enviado.flag: se existe, sai sem enviar.
  - Após envio com sucesso: grava o flag e faz launchctl bootout do próprio agent.
  - Se o envio falhar: loga alto, NÃO grava o flag e sai 1 (retry na próxima janela).

Uso:
  /usr/bin/python3 scripts/lembrete_parte2_consolidacao.py           # modo real
  /usr/bin/python3 scripts/lembrete_parte2_consolidacao.py --teste   # envia [TESTE],
                                                                     # sem flag/bootout
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from email_helper import enviar_email

LABEL        = "br.safie.blog.lembrete-parte2"
PLIST        = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
FLAG         = Path.home() / ".config" / "safie" / "lembrete_parte2_enviado.flag"
DESTINATARIO = "lucas.mantovani@safie.com.br"
ASSUNTO      = "[SAFIE Blog] Executar Parte 2 — consolidação dos 47 clusters de duplicatas"

CORPO = """Lembrete: hoje é dia de executar a PARTE 2 do trabalho de indexação do blog — a consolidação dos 47 clusters de duplicatas (frente passada). O fix dos 87 canonicals e a anti-duplicação (frente futura) já foram feitos em 18/08; esperamos ~2 semanas para o Google digerir antes de mexer no passado.

ANTES de rodar no Code, abra o Chat do projeto (Squad de Mkt) e valide o timing comigo (Claude) — confira no GSC se a indexação do domínio novo já reagiu ao fix dos canonicals. Se sim, siga.

Prompt para colar no Claude Code:

---
Contexto: blog SAFIE unificado em produção (safie.blog.br, repo ~/CLAUDE/Content-Hub-SAFIE, branch main). Executar a consolidação B1 dos 47 clusters de artigos duplicados, conforme o plano já salvo em _archive/plano-consolidacao-clusters-20260818.json. Convenções: git add cirúrgico, backups .bkp, git pull --rebase antes de push, piloto->validacao->rollout, hard-fail em contagem.

Ler o plano JSON salvo e executar:
1. Backup: tar.gz dos 207 HTMLs nao-canonicos + capas + indice.json + sitemap.xml em _archive/.
2. Script scripts/consolidar_clusters.py (--dry-run/--pilot <cluster>/hard-fail): gera as 207 linhas de redirect 301 no arquivo _redirects do Cloudflare Pages (path->path, same-host); remove os HTMLs e capas nao-canonicos; poda indice.json (531->324) e sitemap.xml (577->370, hard-fail se divergir); reponta os 32 links internos "Continue lendo" para o canonico do cluster; regenera llms.txt.
3. ANTES do rollout: conferir no GSC se algum membro nao-canonico de algum cluster tem impressoes reais; se tiver, esse vira o canonico do cluster.
4. Piloto: 1 cluster pequeno -> commit -> validar em producao (301 no lugar, canonico 200, URL fora do sitemap, card fora da home/categoria).
5. Rollout dos 46 restantes -> validacao global -> add cirurgico + commit + push.
6. Pos-deploy: re-submeter o sitemap no GSC e acompanhar cobertura por 2-4 semanas.
Reportar cada etapa; parar e reportar se algo divergir.
---
"""


def _log(msg: str):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] [lembrete-parte2] {msg}")


def _auto_desabilitar():
    """Grava o flag e descarrega o agent. O flag vem PRIMEIRO: o bootout mata o
    próprio processo, então tudo depois dele pode não executar."""
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    FLAG.write_text(f"enviado em {datetime.now():%Y-%m-%d %H:%M:%S}\n", encoding="utf-8")
    _log(f"Flag gravado: {FLAG}")
    r = subprocess.run(
        ["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
        capture_output=True, text=True,
    )
    # Provável não chegar aqui (bootout envia SIGTERM ao job); se chegar, loga.
    _log(f"bootout exit={r.returncode} {r.stderr.strip()}")


def main():
    teste = "--teste" in sys.argv

    if not teste and FLAG.exists():
        _log(f"Flag {FLAG} já existe — e-mail já foi enviado. Nada a fazer.")
        return

    assunto = f"[TESTE] {ASSUNTO}" if teste else ASSUNTO
    try:
        enviar_email(assunto=assunto, corpo=CORPO, destinatario=DESTINATARIO)
    except Exception as e:
        _log(f"FALHA ao enviar o e-mail: {e}")
        _log("Flag NÃO gravado — nova tentativa na próxima janela do agent.")
        sys.exit(1)

    _log(f"E-mail enviado para {DESTINATARIO} ({'modo teste' if teste else 'modo real'}).")
    if teste:
        _log("Modo teste: flag e bootout NÃO executados.")
        return
    _auto_desabilitar()


if __name__ == "__main__":
    main()
