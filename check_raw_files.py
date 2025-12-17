import os
import glob


def check_files():
    print("--- Checking Data Directories ---")

    dirs = ["data/01_raw", "data/02_intermediate"]

    for d in dirs:
        if os.path.exists(d):
            print(f"\nContents of {d}:")
            files = os.listdir(d)
            for f in files:
                size = os.path.getsize(os.path.join(d, f)) / (1024 * 1024)  # Size in MB
                print(f" - {f:<40} ({size:.2f} MB)")
        else:
            print(f"\nDirectory not found: {d}")


if __name__ == "__main__":
    check_files()
