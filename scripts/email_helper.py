"""
email_helper.py — Gmail SMTP para alertas do blog unificado (padrão decisão #006).

Espelha o email_helper.py canônico dos projetos Instagram/Maquina de Conteudo,
com carregamento de secrets self-contained (sem python-dotenv) porque este
pipeline roda sob launchd com ambiente mínimo.

Ordem de busca das credenciais (GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_DESTINATARIO):
  1. Variáveis já presentes no ambiente (não sobrescreve)
  2. ~/.config/safie/blog.env        (canônico deste projeto, se existir)
  3. ~/.config/safie/instagram.env   (fallback — mesma conta Gmail de alerta do ecossistema)
"""
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

_ARQUIVOS_SECRETS = [
    Path.home() / ".config" / "safie" / "blog.env",
    Path.home() / ".config" / "safie" / "instagram.env",
]
_VARS = ("GMAIL_USER", "GMAIL_APP_PASSWORD", "EMAIL_DESTINATARIO")


def _carregar_secrets():
    """Carrega KEY=VALUE dos arquivos de secrets. Não sobrescreve env existente."""
    for arq in _ARQUIVOS_SECRETS:
        if not arq.is_file():
            continue
        if arq.stat().st_mode & 0o077:
            print(f"  [secrets] AVISO: {arq} não está 600 (permissões frouxas).", file=sys.stderr)
        for linha in arq.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, _, valor = linha.partition("=")
            chave = chave.strip()
            if chave in _VARS and chave not in os.environ:
                os.environ[chave] = valor.strip().strip('"').strip("'")


def enviar_email(assunto, corpo, destinatario=None):
    _carregar_secrets()
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")
    dest = destinatario or os.environ.get("EMAIL_DESTINATARIO")

    if not gmail_user or not gmail_password or not dest:
        raise ValueError(
            "Credenciais de email não configuradas (GMAIL_USER/GMAIL_APP_PASSWORD/"
            "EMAIL_DESTINATARIO ausentes no ambiente e em ~/.config/safie/)."
        )

    msg = MIMEMultipart()
    msg["From"] = gmail_user
    msg["To"] = dest
    msg["Subject"] = assunto
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(gmail_user, gmail_password)
        servidor.send_message(msg)


if __name__ == "__main__":
    enviar_email(
        assunto="[Teste] SAFIE Blog unificado — email funcionando",
        corpo="Email de teste do pipeline do blog unificado (safie.blog.br).\n\n"
        "Se chegou aqui, o Gmail SMTP está configurado corretamente.",
    )
    print("Email de teste enviado com sucesso.")
