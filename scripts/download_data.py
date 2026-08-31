#!/usr/bin/env python3
"""Fetch a corpus into the data directory. Datasets are never committed.

Two things here are load-bearing rather than ceremonial:

1. Integrity. Every archive is verified against a pinned SHA-256 before it is
   opened. An archive that fails is deleted, not quarantined.
2. Safe extraction. Archive members are resolved against the destination root
   and anything escaping it is refused (CWE-22, "zip slip"). Python's own
   extractall() was unsafe by default for most of its history; relying on the
   interpreter version to decide whether this is exploitable is not a plan.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

CHUNK = 1 << 20
MAX_ARCHIVE_BYTES = 8 * 1024**3  # refuse absurd archives rather than filling the disk


@dataclass(frozen=True)
class Corpus:
    name: str
    url: str
    sha256: str
    note: str


# NOTE: fill in the pinned digest the first time you download a corpus, using
# the value this script prints on a checksum mismatch. Do not paste a digest
# from anywhere but your own verified download.
REGISTRY: dict[str, Corpus] = {
    "cord": Corpus(
        name="cord",
        url="https://huggingface.co/datasets/naver-clova-ix/cord-v2/resolve/main/data/train-00000-of-00004.parquet",
        sha256="",
        note="CORD receipts. Start here: small, well annotated, permissively licensed.",
    ),
    "midv500": Corpus(
        name="midv500",
        url="",
        sha256="",
        note="Identity documents. Closest to the KYC setting; check the licence before use.",
    ),
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path) -> None:
    if not url.lower().startswith("https://"):
        raise ValueError(f"refusing non-HTTPS source: {url!r}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    # urlopen verifies the certificate chain and hostname by default. Do not
    # pass a context that weakens that.
    with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as out:
        total = 0
        while chunk := response.read(CHUNK):
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                tmp.unlink(missing_ok=True)
                raise ValueError("archive exceeds the size ceiling; refusing")
            out.write(chunk)
    tmp.replace(dest)


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def safe_extract(archive: Path, dest: Path) -> None:
    """Extract, refusing any member that would land outside `dest`."""
    dest.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for member in zf.infolist():
                target = dest / member.filename
                if not _is_within(dest, target):
                    raise ValueError(f"archive member escapes destination: {member.filename!r}")
            zf.extractall(dest)
        return

    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    raise ValueError(f"refusing link member: {member.name!r}")
                if not _is_within(dest, dest / member.name):
                    raise ValueError(f"archive member escapes destination: {member.name!r}")
            tf.extractall(dest)
        return

    shutil.copy2(archive, dest / archive.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", choices=sorted(REGISTRY))
    parser.add_argument("--data-dir", type=Path, default=Path("./data"))
    parser.add_argument("--extract", action="store_true")
    args = parser.parse_args()

    corpus = REGISTRY[args.corpus]
    if not corpus.url:
        print(f"No source URL pinned for {corpus.name!r} yet. {corpus.note}", file=sys.stderr)
        return 2

    target_dir = args.data_dir.expanduser().resolve() / corpus.name
    archive = target_dir / Path(corpus.url).name

    if not archive.exists():
        print(f"Downloading {corpus.name} ...")
        download(corpus.url, archive)

    actual = sha256_of(archive)
    if not corpus.sha256:
        print(f"No digest pinned. Verify this download, then pin:\n  sha256 = {actual!r}")
        return 3
    if actual != corpus.sha256:
        archive.unlink(missing_ok=True)
        print(
            f"Checksum mismatch for {corpus.name}; deleted.\n"
            f"  expected {corpus.sha256}\n"
            f"  actual   {actual}",
            file=sys.stderr,
        )
        return 1

    print(f"Verified {archive}")
    if args.extract:
        safe_extract(archive, target_dir)
        print(f"Extracted into {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
