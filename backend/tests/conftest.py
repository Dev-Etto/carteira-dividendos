"""Configuração comum: banco temporário, scheduler e carga inicial desligados antes de qualquer import do app."""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["INITIAL_SYNC"] = "false"
