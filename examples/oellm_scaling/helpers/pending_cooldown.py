#!/usr/bin/env python3
import sys
from pathlib import Path

def main():

    # CLI args: LOGS stable_name decay_name iter
    ckpt_folder, stable_name, decay_name, iter_str = sys.argv[1:]

    # Read and write paths
    read_folder = Path(ckpt_folder) / stable_name
    write_folder = Path(ckpt_folder) / decay_name

    # Format iteration as a 7-digit, zero-padded decimal number
    iter_dir = f"iter_{int(iter_str):07d}"

    # Target directory to look for
    target = read_folder / iter_dir

    # Check if a matching directory was found and create the symlink.
    if target.is_dir():
        write_folder.mkdir(parents=True, exist_ok=True)
        link_path = write_folder / iter_dir
        if link_path.exists() or link_path.is_symlink():
            # Symlink or file already exists — nothing to do
            print(1)
            sys.exit(0)
        link_path.symlink_to(target.resolve())
        (write_folder / "latest_checkpointed_iteration.txt").write_text(f"{iter_str}\n")
        print(1)
        sys.exit(0)

    else:
        print(0)
        sys.exit(0)

if __name__ == "__main__":
    main()
