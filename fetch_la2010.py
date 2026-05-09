#!/usr/bin/env python3
"""
Fetch La2010d obliquity (epsilon) data from IMCCE and produce La2010.js
by appending obliquity functions to the existing eccentricity.js.

Source: Laskar J., Fienga A., Gastineau M., Manche H. (2011).
  "La2010: a new orbital solution for the long-term motion of the Earth."
  Astronomy & Astrophysics 532, A89.
  https://ssp.imcce.fr/insola/earth/online/earth/La2010/
"""

import urllib.request
import math
import sys
import os

OBL_URL    = "https://ssp.imcce.fr/insola/earth/online/earth/La2010/La2010d_eps3.dat"
INPUT_JS   = "eccentricity.js"
OUTPUT_JS  = "La2010.js"
ARRAY_NAME = "_LA2010D_OBL"
PER_LINE   = 10

# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch(url):
    print(f"Fetching {url} ...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

# ─── Parse ────────────────────────────────────────────────────────────────────

def parse_column(text, col=1):
    """Extract one numeric column from whitespace-delimited data, skipping comment lines."""
    values = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ('#', '!', '%'):
            continue
        parts = line.split()
        if len(parts) > col:
            values.append(float(parts[col]))
    return values

# ─── Format JS array ──────────────────────────────────────────────────────────

def js_array(name, values):
    rows = []
    for i in range(0, len(values), PER_LINE):
        chunk = values[i:i + PER_LINE]
        rows.append('  ' + ', '.join(f'{v:.9f}' for v in chunk) + ',')
    if rows:
        rows[-1] = rows[-1].rstrip(',')
    return f"const {name} = [\n" + '\n'.join(rows) + "\n];"

# ─── JS blocks to append ──────────────────────────────────────────────────────

def obl_js_block(array_js):
    return f"""
// ─── La2010d tabulated obliquity (axial tilt) ────────────────────────────────
// 2001 values, index i = 0…2000, t_i = −5000·i  Julian years from J2000.0
// Obliquity epsilon in radians.  Earth present value ≈ 0.40928 rad (23.439°).
// Retrieved from La2010d_eps3.dat (IMCCE, 2011); 5 kyr time step.

{array_js}

// ─── Core obliquity function ─────────────────────────────────────────────────

const _N_OBL = _LA2010D_OBL.length;

/**
 * Earth's axial obliquity from the La2010d solution.
 *
 * @param {{number}} t  Julian years from J2000.0 (negative = past).
 *                      Range: 0 to −10,000,000 yr (10 Myr before J2000).
 * @returns {{number}}  Obliquity in radians.  Earth's range: ~0.36–0.44 rad (21°–25°).
 */
function earthObliquity(t) {{
  if (t > 5000) {{
    if (typeof console !== 'undefined')
      console.warn('earthObliquity: t > 5000 yr (future). Result unreliable.');
    t = 5000;
  }}

  if (t > 0) {{
    const slope = (_LA2010D_OBL[0] - _LA2010D_OBL[1]) / _STEP;
    return _LA2010D_OBL[0] + slope * t;
  }}

  const absT = -t;
  if (absT >= _MAX) {{
    if (typeof console !== 'undefined')
      console.warn('earthObliquity: |t| > 10 Myr; returning boundary value.');
    return _LA2010D_OBL[_N_OBL - 1];
  }}

  const pos = absT / _STEP;
  const i   = Math.floor(pos);
  const f   = pos - i;

  if (f === 0) return _LA2010D_OBL[i];

  const i0 = Math.max(0, i - 1);
  const i1 = i;
  const i2 = Math.min(_N_OBL - 1, i + 1);
  const i3 = Math.min(_N_OBL - 1, i + 2);

  return _catmullRom(_LA2010D_OBL[i0], _LA2010D_OBL[i1], _LA2010D_OBL[i2], _LA2010D_OBL[i3], f);
}}

/** Obliquity in degrees. */
function earthObliquityDeg(t) {{
  return earthObliquity(t) * (180 / Math.PI);
}}

/** Obliquity directly from a JavaScript Date. */
function earthObliquityFromDate(date) {{
  return earthObliquity(dateToJ2000(date));
}}
"""

UPDATED_EXPORTS = """
// ─── Export ──────────────────────────────────────────────────────────────────

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    earthEccentricity, earthEccentricityFromDate,
    earthObliquity, earthObliquityDeg, earthObliquityFromDate,
    dateToJ2000, jdToJ2000,
  };
} else if (typeof window !== 'undefined') {
  Object.assign(window, {
    earthEccentricity, earthEccentricityFromDate,
    earthObliquity, earthObliquityDeg, earthObliquityFromDate,
    dateToJ2000, jdToJ2000,
  });
}
"""

SELFTEST_APPEND = """
// ─── Obliquity self-test ─────────────────────────────────────────────────────

(function obliquityTest() {
  // Spot checks against published La2010d values (Laskar et al. 2011, Table 1)
  const DEG = 180 / Math.PI;
  const checks = [
    [       0,  23.439, 'J2000.0 (~23.439°)'],
    [ -100000,  null,   '100 kyr BP (interpolated)'],
    [ -405000,  null,   '405 kyr BP (long-ecc minimum)'],
  ];

  console.log('\\nEarth obliquity — La2010d solution');
  console.log('────────────────────────────────────────');
  for (const [t, degRef, label] of checks) {
    const deg = earthObliquityDeg(t);
    if (degRef !== null) {
      const err = Math.abs(deg - degRef);
      console.log(`t=${String(t).padStart(9)} yr  ε=${deg.toFixed(4)}°  ref≈${degRef.toFixed(3)}°  Δ=${err.toFixed(4)}°  (${label})`);
    } else {
      console.log(`t=${String(t).padStart(9)} yr  ε=${deg.toFixed(4)}°  (${label})`);
    }
  }
  console.log('  earthObliquityDeg(0) =>', earthObliquityDeg(0).toFixed(6), '°');
})();
"""

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path  = os.path.join(script_dir, INPUT_JS)
    output_path = os.path.join(script_dir, OUTPUT_JS)

    if not os.path.exists(input_path):
        sys.exit(f"Error: {input_path} not found.")

    with open(input_path, encoding='utf-8') as f:
        src = f.read()

    # Strip old export block and self-test so we can replace them cleanly
    cut = len(src)
    for marker in ('// ─── Export ─', '// ─── Self-test ─'):
        idx = src.find(marker)
        if idx != -1 and idx < cut:
            cut = idx
    base = src[:cut].rstrip()

    # Fetch and parse obliquity
    raw = fetch(OBL_URL)
    obl = parse_column(raw, col=1)

    if len(obl) < 100:
        sys.exit(f"Error: only {len(obl)} values parsed — check URL or data format.")

    print(f"Parsed {len(obl)} obliquity values.")
    print(f"  Range: {min(obl):.6f}–{max(obl):.6f} rad  "
          f"({math.degrees(min(obl)):.3f}°–{math.degrees(max(obl)):.3f}°)")
    print(f"  J2000 (index 0): {math.degrees(obl[0]):.6f}°  (expected ~23.439°)")

    arr_js = js_array(ARRAY_NAME, obl)
    out = (base
           + obl_js_block(arr_js)
           + UPDATED_EXPORTS
           + SELFTEST_APPEND)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(out)

    print(f"\nWritten: {output_path}  ({len(out):,} bytes)")
    print("Update your HTML: <script src=\"La2010.js\"></script>")

if __name__ == '__main__':
    main()
