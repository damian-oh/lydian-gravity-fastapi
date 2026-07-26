"""Delete demo accounts older than a cutoff.

Demo mode creates one throwaway user per visitor, so a long-running deployment
accumulates rows. Songs, sections, chords and melodic notes go with the user
via the existing cascade on User.song_sketches.

Accounts are selected by the is_demo flag rather than by their email address, so
a demo visitor who edits their email through PATCH /users/me is still purged and
a registered account that happens to look like a demo address never is.

Usage:
    uv run python scripts/purge_demo_users.py            # older than 7 days
    uv run python scripts/purge_demo_users.py --days 1
    uv run python scripts/purge_demo_users.py --dry-run
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

# Imported for its side effect: every model has to be registered before the
# User.song_sketches relationship can resolve, and the cascade is what removes a
# purged account's songs.
from app.db.base import User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Delete demo users created more than this many days ago (default: 7).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without deleting it.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)

    db = SessionLocal()
    try:
        stale_users = list(
            db.scalars(
                select(User).where(
                    User.is_demo.is_(True),
                    User.created_at < cutoff,
                )
            )
        )

        if not stale_users:
            print(f"No demo users older than {args.days} day(s).")
            return 0

        if args.dry_run:
            print(f"Would delete {len(stale_users)} demo user(s):")
            for user in stale_users:
                print(f"  {user.id}\t{user.email}\t{user.created_at}")
            return 0

        for user in stale_users:
            db.delete(user)

        db.commit()
        print(f"Deleted {len(stale_users)} demo user(s) created before {cutoff}.")
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
