"""Background Night Shift worker. Runs with no UI open; processes scheduled jobs.
Note: it only runs while this computer is awake and this process is running."""

import time

from dotenv import load_dotenv

load_dotenv()

from salis import nightshift  # noqa: E402

if __name__ == "__main__":
    print("Night Shift worker running. Ctrl+C to stop.")
    while True:
        for job_id in nightshift.run_due_jobs():
            print(f"processed job {job_id}")
        time.sleep(10)
