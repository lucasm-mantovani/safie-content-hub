"""
alertar_falha_publicacao.py — Alerta por e-mail quando um nicho falha no pipeline.

Chamado pelo rodar_diario.sh nos branches de falha das etapas gerar, seo e
publicar (decisão #006: nenhuma falha do pipeline automático pode ficar
silenciosa). Nunca deve derrubar o pipeline: qualquer erro aqui é impresso e
o exit é 0.

Uso: python3 scripts/alertar_falha_publicacao.py <nicho> [--etapa gerar|seo|publicar] [--dry]
  --etapa  etapa que falhou; ajusta o assunto (padrão: publicar).
  --dry    monta o e-mail e imprime no stdout em vez de enviar (validação).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASTA = Path(__file__).resolve().parent.parent
LINHAS_DE_LOG = 40

ROTULO_ETAPA = {
    "gerar": "Falha na GERAÇÃO automática",
    "seo": "Falha na otimização SEO automática",
    "publicar": "Falha na publicação automática",
}


def montar_email(nicho, etapa="publicar"):
    hoje = date.today().isoformat()
    rotulo = ROTULO_ETAPA.get(etapa, ROTULO_ETAPA["publicar"])
    assunto = f"[SAFIE Blog] {rotulo} — {nicho} {hoje}"

    log = PASTA / "logs" / f"pipeline_{hoje}.log"
    if log.is_file():
        cauda = "".join(log.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[-LINHAS_DE_LOG:])
    else:
        cauda = f"(log {log} não encontrado)"

    corpo = (
        f"O pipeline diário do blog unificado (safie.blog.br) falhou na etapa "
        f"'{etapa}' do nicho '{nicho}' em {hoje}.\n\n"
        f"O artigo NÃO foi publicado. Sem intervenção, o gap continua nos próximos dias.\n\n"
        f"Últimas {LINHAS_DE_LOG} linhas de logs/pipeline_{hoje}.log:\n"
        f"{'-' * 60}\n{cauda}{'-' * 60}\n\n"
        f"Diagnóstico: verificar o traceback acima; repo em ~/CLAUDE/Content-Hub-SAFIE.\n"
    )
    return assunto, corpo


def main():
    argv = sys.argv[1:]
    dry = "--dry" in argv
    etapa = "publicar"
    if "--etapa" in argv:
        i = argv.index("--etapa")
        if i + 1 < len(argv):
            etapa = argv[i + 1]
    nicho = argv[0] if argv and not argv[0].startswith("--") else "desconhecido"

    assunto, corpo = montar_email(nicho, etapa)
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
