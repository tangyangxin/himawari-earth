from downloader import generate_earth
from processor import process_outputs

import traceback


def main():
    print("=" * 40)
    print("Himawari Earth Generator")
    print("=" * 40)

    try:
        print("\n[1] Download")
        generate_earth()

        print("\n[2] Process")
        process_outputs()

        print("\nDONE")

    except Exception:
        print("\nFAILED")
        traceback.print_exc()


if __name__ == "__main__":
    main()