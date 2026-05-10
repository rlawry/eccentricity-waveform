#!/usr/bin/env python3
"""
Fetch pibar (longitude of perihelion) from INSOLN.LA2004.BTL.ASC and print
the _LA2004_PIBAR JavaScript array for insertion into La2010.js.

Source: Laskar et al. (2004), La2004 solution.
File columns: time(yr) | e | obliquity(rad) | pibar(rad)
We sample every 5th row (1 kyr → 5 kyr steps), 2001 values, t=0 to -10 Myr.
"""

import urllib.request
import math

URL      = "https://ssp.imcce.fr/insola/earth/online/earth/La2004/INSOLN.LA2004.BTL.ASC"
PER_LINE = 10

def fetch(url):
    print(f"Fetching {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()

def main():
    raw = fetch(URL)

    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line[0] in ('#', '!', '%'):
            continue
        parts = line.split()
        if len(parts) >= 4:
            rows.append(parts)

    print(f"Total rows parsed: {len(rows)}")

    # Sample every 5th row (rows are at 1 kyr steps; we want 5 kyr steps)
    sampled = rows[::5][:2001]
    pibar = [float(r[3].replace('D', 'E').replace('d', 'e')) for r in sampled]

    print(f"Sampled {len(pibar)} values at 5 kyr steps.")
    print(f"  pibar[0] = {pibar[0]:.9f} rad = {math.degrees(pibar[0]):.4f} deg  (J2000, expected ~103°)")
    print(f"  pibar[-1] = {pibar[-1]:.9f} rad  (10 Myr BP boundary)")
    print()

    # Print the JS array
    lines = ["const _LA2004_PIBAR = ["]
    for i in range(0, len(pibar), PER_LINE):
        chunk = pibar[i:i + PER_LINE]
        row = '  ' + ', '.join(f'{v:.9f}' for v in chunk) + ','
        lines.append(row)
    lines[-1] = lines[-1].rstrip(',')
    lines.append("];")
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
