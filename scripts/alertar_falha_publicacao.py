"""
alertar_falha_publicacao.py — Alerta por e-mail quando um nicho falha na publicação.

Chamado pelo rodar_diario.sh no branch de falha do publicar.py (decisão #006:
nenhuma falha de publicação automática pode ficar silenciosa). Nunca deve
derrubar o pipeline: qualquer erro aqui é impresso e o exit é 0.

Uso: python3 scripts/alertar_falha_publicacao.py <nicho> [--dry]
  --dry  monta o e-mail e imprime no stdout em vez de enviar (validação).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASTA = Path(__file__).resolve().parent.parent
LINHAS_DE_LOG = 40


def montar_email(nicho):
    hoje = date.today().isoformat()
    assunto = f"[SAFIE Blog] Falha na publicação automática — {nicho} {hoje}"

    log = PASTA / "logs" / f"pipeline_{hoje}.log"
    if log.is_file():
        cauda = "".join(log.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-LINHAS_DE_LOG:])
    else:
        cauda = f"(log {log} não encontrado)"

    corpo = (
        f"O pipeline diário do blog unificado (safie.blog.br) falhou ao publicar "
        f"o nicho '{nicho}' em {hoje}.\n\n"
        f"O artigo NÃO foi publicado. Sem intervenção, o gap continua nos próximos dias.\n\n"
        f"Últimas {LINHAS_DE_LOG} linhas de logs/pipeline_{hoje}.log:\n"
        f"{'-' * 60}\n{cauda}{'-' * 60}\n\n"
        f"Diagnóstico: verificar o traceback acima; repo em ~/CLAUDE/Content-Hub-SAFIE.\n"
    )
    return assunto, corpo


def main():
    args = [a for a in sys.argv[1:] if a != "--dry"]
    dry = "--dry" in sys.argv[1:]
    nicho = args[0] if args else "desconhecido"

    assunto, corpo = montar_email(nicho)
    if dry:
        print(f"[DRY] Assunto: {assunto}")
        print(f"[DRY] Corpo:\n{corpo}")
        return

    try:
        from email_helper import enviar_email
        enviar_email(assunto, corpo)
        print(f"[alerta] E-mail de falha enviado ({nicho}).")
    except Exception as e:  # noqa: BLE001 — alerta nunca pode derrubar o pipeline
        print(f"[alerta] ERRO ao enviar e-mail de falha ({nicho}): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
