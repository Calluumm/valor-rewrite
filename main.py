import os, time, platform, multiprocessing
from core.bot import run_bot


if __name__ == "__main__":
    if platform.system() == "Darwin": # Darwin = MacOS
        multiprocessing.set_start_method("fork")

    os.environ["TZ"] = "Europe/London"
    if hasattr(time, "tzset"): #windows guard for my sanity
        time.tzset()


    directories = [
        "storages",                  # Root storage folder
        "storages/user_settings",    # Per-user configuration/settings
        "storages/guild_settings"    # Per-guild configuration/settings
    ]

    for dir_path in directories:
        try:
            # Create the directory if it doesn't already exist.
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            # Log an error if directory creation fails.
            print(f"Error creating directory '{dir_path}': {e}")

    run_bot()
