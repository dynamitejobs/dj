"""Daily cron: pull yesterday's analytics into our internal BI."""

from datetime import date, timedelta
import json
from dynamitejobs import DJ


def main() -> None:
    dj = DJ()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()

    funnel = dj.analytics_funnel(from_=yesterday, to=today)
    sources = dj.analytics_sources(from_=yesterday, to=today)
    per_job = dj.analytics_jobs(from_=yesterday, to=today)

    out = {
        "date": yesterday,
        "funnel": funnel,
        "sources": sources,
        "per_job": per_job,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
