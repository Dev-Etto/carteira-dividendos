"""Configuração comum: banco temporário e scheduler desligado antes de qualquer import do app."""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ENABLE_SCHEDULER"] = "false"
