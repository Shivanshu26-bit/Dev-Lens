import os
import sys
import logging
from typing import Optional
from alembic.config import Config
from alembic import command

logger = logging.getLogger("devlens.migrate")


def get_alembic_config(config_path: Optional[str] = None) -> Config:
    """
    Locates and returns the Alembic Config instance.
    Defaults to alembic.ini located in the backend root directory.
    """
    if config_path is None:
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(backend_dir, "alembic.ini")

    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Alembic configuration file not found at: {config_path}")

    return Config(config_path)


def run_migrations(config_path: Optional[str] = None, target: str = "head") -> None:
    """
    Executes database schema migrations up to the target revision (defaults to 'head').
    Designed for safe, idempotent pre-startup execution in production container releases.
    """
    alembic_cfg = get_alembic_config(config_path)
    logger.info(f"Starting database migration to target '{target}' using config: {alembic_cfg.config_file_name}")
    command.upgrade(alembic_cfg, target)
    logger.info(f"Database migrations successfully applied to target '{target}'.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    target_rev = sys.argv[1] if len(sys.argv) > 1 else "head"
    run_migrations(target=target_rev)
