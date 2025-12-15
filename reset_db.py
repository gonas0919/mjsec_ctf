import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")

def main():
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    patterns = [
        os.path.join(INSTANCE_DIR, "ctf.db*"),
        os.path.join(BASE_DIR, "ctf.db*"),
    ]
    removed = 0
    for pat in patterns:
        for f in glob.glob(pat):
            try:
                os.remove(f)
                removed += 1
            except OSError:
                pass

    print(f"[reset_db] removed files: {removed}")

if __name__ == "__main__":
    main()
