#!/usr/bin/env python3
"""Check a train/val/test image dataset for near-duplicate leakage, and optionally re-split it.

What it does
  1. Hashes every image (16x16 difference hash, 256 bits) in all 8 flips/rotations.
  2. For each val and test image, finds the closest train image (and test -> val)
     and reports how many are near-duplicates (Hamming distance <= --threshold).
  3. If your filenames contain a board ID, --group-regex also reports board IDs that
     appear in more than one split.
  4. With --resplit OUT_DIR it writes leak-reduced train/val/test file lists, keeping each
     group (board ID, or cluster of near-duplicates) inside one split.

What it can NOT do
  A global hash finds exact, re-compressed, flipped and rotated copies. It will NOT find two
  different crops cut from neighbouring or overlapping parts of the same board. For that,
  put the board ID in --group-regex if your filenames carry it. A clean result here lowers,
  but does not remove, the leakage risk.

Usage
  python leakage_check.py --root path/to/printed-circuit-board-pcb-defects
  python leakage_check.py --root DATA --group-regex "^(\\d+)_" --resplit lists/
Requires: numpy, pillow.
"""
import argparse
import csv
import random
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
POPCOUNT = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)
SPLITS = ("train", "val", "test")


def find_images(folder):
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in IMG_EXT)


def pack_hash(a, size):
    bits = (a[:size, 1:size + 1] > a[:size, :size]).astype(np.uint8)
    return np.packbits(bits.ravel())


def variant_hashes(path, size):
    """Return (8, size*size/8) uint8 array: hashes of the 8 flips/rotations."""
    img = Image.open(path).convert("L").resize((size + 1, size + 1), Image.LANCZOS)
    a = np.asarray(img, dtype=np.int16)
    out = []
    for flip in (False, True):
        b = np.fliplr(a) if flip else a
        for k in range(4):
            out.append(pack_hash(np.rot90(b, k), size))
    return np.stack(out)


def load_split(root, name, size):
    folder = root / name
    if not folder.is_dir():
        return None
    paths = find_images(folder)
    hashes = []
    for i, p in enumerate(paths, 1):
        try:
            hashes.append(variant_hashes(p, size))
        except Exception as exc:  # unreadable file: report and skip
            print(f"  skipped {p}: {exc}", file=sys.stderr)
            paths[i - 1] = None
        if i % 1000 == 0:
            print(f"  {name}: hashed {i}/{len(paths)}")
    paths = [p for p in paths if p is not None]
    return paths, np.stack(hashes) if hashes else np.zeros((0, 8, size * size // 8), np.uint8)


def nearest(queries, refs, chunk=16):
    """queries (n,8,B) vs refs (m,B): min Hamming distance over the 8 variants."""
    n = len(queries)
    dist = np.full(n, 10 ** 6, dtype=np.int32)
    idx = np.full(n, -1, dtype=np.int64)
    if len(refs) == 0:
        return dist, idx
    for s in range(0, n, chunk):
        q = queries[s:s + chunk]
        x = q[:, :, None, :] ^ refs[None, None, :, :]
        d = POPCOUNT[x].sum(axis=-1, dtype=np.int32).min(axis=1)  # (q, m)
        j = d.argmin(axis=1)
        dist[s:s + chunk] = d[np.arange(len(q)), j]
        idx[s:s + chunk] = j
    return dist, idx


def compare(name_q, name_r, data, threshold, writer):
    pq, hq = data[name_q]
    pr, hr = data[name_r]
    dist, idx = nearest(hq, hr[:, 0, :])
    near = dist <= threshold
    print(f"\n{name_q} -> {name_r}: {int(near.sum())} of {len(pq)} images "
          f"({100 * near.mean():.1f}%) have a near-duplicate (distance <= {threshold}/256)")
    if len(dist):
        qs = np.percentile(dist, [0, 5, 25, 50])
        print(f"  nearest-distance percentiles 0/5/25/50: {qs[0]:.0f} / {qs[1]:.0f} / {qs[2]:.0f} / {qs[3]:.0f}")
    for i in np.flatnonzero(near):
        writer.writerow([name_q, pq[i], name_r, pr[idx[i]], int(dist[i])])
    return float(near.mean()) if len(dist) else 0.0


def group_overlap(data, regex):
    pattern = re.compile(regex)
    groups = {}
    for name in SPLITS:
        if name not in data:
            continue
        for p in data[name][0]:
            m = pattern.search(p.stem)
            if m:
                groups.setdefault(m.group(1), set()).add(name)
    shared = {g: s for g, s in groups.items() if len(s) > 1}
    print(f"\nBoard IDs found: {len(groups)}; present in more than one split: {len(shared)}")
    for g, s in list(shared.items())[:10]:
        print(f"  {g}: {sorted(s)}")
    return pattern


def resplit(data, out_dir, threshold, pattern, val_frac, test_frac, seed):
    paths = [p for name in SPLITS if name in data for p in data[name][0]]
    hashes = np.concatenate([data[name][1] for name in SPLITS if name in data])
    n = len(paths)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    if pattern is not None:
        first = {}
        missing = 0
        for i, p in enumerate(paths):
            m = pattern.search(p.stem)
            if not m:
                missing += 1
                continue
            union(i, first.setdefault(m.group(1), i))
        print(f"\nGrouped by board ID; {missing} files did not match the regex (kept as singletons).")
    refs = hashes[:, 0, :]
    for s in range(0, n, 16):
        q = hashes[s:s + 16]
        x = q[:, :, None, :] ^ refs[None, None, :, :]
        d = POPCOUNT[x].sum(axis=-1, dtype=np.int32).min(axis=1)
        for qi, rj in np.argwhere(d <= threshold):
            if s + qi != rj:
                union(s + qi, int(rj))

    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    groups = list(clusters.values())
    random.Random(seed).shuffle(groups)
    targets = {"test": test_frac * n, "val": val_frac * n}
    out = {"train": [], "val": [], "test": []}
    for g in groups:
        pick = "train"
        for name in ("test", "val"):
            if len(out[name]) < targets[name]:
                pick = name
                break
        out[pick].extend(g)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, members in out.items():
        (out_dir / f"{name}.txt").write_text("\n".join(str(paths[i]) for i in sorted(members)) + "\n")
    print(f"Wrote {out_dir}/train.txt, val.txt, test.txt  "
          f"({len(out['train'])} / {len(out['val'])} / {len(out['test'])} images; "
          f"largest group {max(len(g) for g in groups)} images)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True, type=Path, help="folder containing train/ val/ test/")
    ap.add_argument("--threshold", type=int, default=10, help="max Hamming distance (of 256 bits) to call a near-duplicate")
    ap.add_argument("--hash-size", type=int, default=16, help="hash is size x size bits (default 16)")
    ap.add_argument("--group-regex", default=None, help="regex with ONE capture group giving the board ID from a filename stem")
    ap.add_argument("--resplit", type=Path, default=None, help="write leak-reduced split lists to this folder")
    ap.add_argument("--val-frac", type=float, default=0.1)
    ap.add_argument("--test-frac", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--fail-frac", type=float, default=None, help="exit 1 if any near-duplicate fraction exceeds this (0-1)")
    ap.add_argument("--matches-csv", type=Path, default=Path("leak_matches.csv"))
    args = ap.parse_args()

    if args.hash_size % 8 != 0:
        ap.error("--hash-size must be a multiple of 8")
    data = {}
    for name in SPLITS:
        print(f"Hashing {name} ...")
        loaded = load_split(args.root, name, args.hash_size)
        if loaded is None:
            print(f"  folder {args.root / name} not found, skipping")
            continue
        data[name] = loaded
        sample = [p.name for p in loaded[0][:3]]
        print(f"  {len(loaded[0])} images; sample names: {sample}")
    if "train" not in data or len(data) < 2:
        sys.exit("Need a train folder and at least one of val/test.")

    fracs = []
    with open(args.matches_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_split", "query_file", "match_split", "match_file", "distance"])
        for q, r in (("val", "train"), ("test", "train"), ("test", "val")):
            if q in data and r in data:
                fracs.append(compare(q, r, data, args.threshold, w))
    print(f"\nMatches written to {args.matches_csv}")

    pattern = group_overlap(data, args.group_regex) if args.group_regex else None
    if args.resplit:
        resplit(data, args.resplit, args.threshold, pattern, args.val_frac, args.test_frac, args.seed)
    if args.fail_frac is not None and any(x > args.fail_frac for x in fracs):
        sys.exit(1)


if __name__ == "__main__":
    main()
