"""Post a paid job via the Company API.

Prerequisites:
  - DJ_API_KEY set (or ~/.env.dj saved via `dj setup --api-key ...`)
  - The key has write scope (default: all)
  - Company has a card on file (set via the DJ dashboard once)
  - COMPANY_API_BILLING_LIVE=true on the server (otherwise publish returns a stub)
"""

from dynamitejobs import DJ, DJError


def main() -> None:
    dj = DJ()

    # 1. Create the draft
    draft = dj.create_job(
        title="Senior Backend Engineer (Remote)",
        description="We're looking for a backend engineer to own our data platform...",
        applyUrl="https://acme.example/apply/abc",
        salaryMin=120_000,
        salaryMax=180_000,
        location="Remote (Worldwide)",
        category="engineering",
    )
    job_id = draft["id"]
    print(f"Draft created: {job_id}")

    # 2. Publish — this charges the card on file
    try:
        published = dj.publish_job(job_id)
        print(f"Published! Charge ID: {published['chargeId']}")
        print(f"Receipt: {published['receiptUrl']}")
    except DJError as e:
        if e.status == 402:
            print(f"Card-on-file check failed: {e.body.get('message')}")
            print("Add a payment method in the DJ dashboard before scripting publishes.")
            return
        raise


if __name__ == "__main__":
    main()
