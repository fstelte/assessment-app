#!/usr/bin/env python3
"""Encrypt a backup file using Fernet. Called from backup-db.sh."""
import sys
from cryptography.fernet import Fernet


def main():
    if len(sys.argv) != 4:
        print("Usage: encrypt_backup.py <infile> <outfile> <key>", file=sys.stderr)
        sys.exit(1)
    infile, outfile, key = sys.argv[1], sys.argv[2], sys.argv[3]
    with open(infile, "rb") as f:
        data = f.read()
    encrypted = Fernet(key.encode()).encrypt(data)
    with open(outfile, "wb") as f:
        f.write(encrypted)


if __name__ == "__main__":
    main()
