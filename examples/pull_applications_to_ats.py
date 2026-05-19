"""Pull all applications for a job and forward them to your ATS (Greenhouse / Lever / etc).

Demonstrates cursor pagination.
"""

import os
from dynamitejobs import DJ


def push_to_ats(application: dict) -> None:
    # Replace with your ATS's create-candidate API.
    name = application.get("name", "(unknown)")
    print(f"  -> ATS: {name} ({application['id']})")


def main(job_id: str) -> None:
    dj = DJ()
    cursor = None
    count = 0
    while True:
        page = dj.applications(job_id, cursor=cursor, limit=100)
        for app in page["applications"]:
            push_to_ats(app)
            count += 1
        cursor = page.get("cursor") or None
        if not cursor:
            break
    print(f"Synced {count} applications to ATS.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <jobID>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
