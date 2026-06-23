"""Database migration utility script."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command


def run_migration(action: str = "upgrade"):
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))

    if action == "upgrade":
        command.upgrade(alembic_cfg, "head")
        print("✓ Database upgraded to latest revision")
    elif action == "downgrade":
        command.downgrade(alembic_cfg, "-1")
        print("✓ Database downgraded by one revision")
    elif action == "history":
        command.history(alembic_cfg)
    elif action == "current":
        command.current(alembic_cfg)
    elif action == "autogenerate":
        command.revision(alembic_cfg, autogenerate=True, message="auto migration")
        print("✓ Auto-generated migration created")
    else:
        print(f"Unknown action: {action}")
        print("Available: upgrade, downgrade, history, current, autogenerate")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    run_migration(action)
