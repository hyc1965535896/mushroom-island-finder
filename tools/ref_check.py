#!/usr/bin/env python3
"""Independent Python transcription of cubiomes 1.18+ climate biome sampling,
used to debug the Java port. Directly transcribed from cubiomes
rng.h/noise.c/biomenoise.c (float32 emulation where C uses float).

Usage: python ref_check.py [mcver]   (default 18; prints golden hash + ids)
"""
import math, re, struct, sys, pathlib

MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1
TABLES = pathlib.Path(__file__).resolve().parent.parent / "_ref" / "cubiomes-master" / "tables"

def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]

#------------------------------------------------------------------------------
# Xoroshiro128++ (rng.h)
#------------------------------------------------------------------------------
def rotl64(x, b):
    return ((x << b) | (x >> (64 - b))) & MASK64

class Xoroshiro:
    def __init__(self, value=None):
        self.lo = self.hi = 0
        if value is not None:
            self.set_seed(value)
    def set_seed(self, value):
        XL = 0x9e3779b97f4a7c15; XH = 0x6a09e667f3bcc909
        A = 0xbf58476d1ce4e5b9;  B = 0x94d049bb133111eb
        l = (value ^ XH) & MASK64
        h = (l + XL) & MASK64
        l = ((l ^ (l >> 30)) * A) & MASK64
        h = ((h ^ (h >> 30)) * A) & MASK64
        l = ((l ^ (l >> 27)) * B) & MASK64
        h = ((h ^ (h >> 27)) * B) & MASK64
        self.lo = l ^ (l >> 31)
        self.hi = h ^ (h >> 31)
    def next_long(self):
        l, h = self.lo, self.hi
        n = (rotl64((l + h) & MASK64, 17) + l) & MASK64
        h ^= l
        self.lo = (rotl64(l, 49) ^ h ^ ((h << 21) & MASK64)) & MASK64
        self.hi = rotl64(h, 28)
        return n
    def next_int(self, n):
        r = (self.next_long() & 0xFFFFFFFF) * n
        if (r & MASK32) < n:
            lim = ((~n + 1) & MASK32) % n
            while (r & MASK32) < lim:
                r = (self.next_long() & 0xFFFFFFFF) * n
        return r >> 32
    def next_double(self):
        return (self.next_long() >> 11) * 1.1102230246251565E-16

#------------------------------------------------------------------------------
# Perlin noise (noise.c)
#------------------------------------------------------------------------------
MD5_OCT = [
    (0xb198de63a8012672, 0x7b84cad43ef7b5a8), # octave_-12
    (0x0fd787bfbc403ec3, 0x74a4a31ca21b48b8), # octave_-11
    (0x36d326eed40efeb2, 0x5be9ce18223c636a), # octave_-10
    (0x082fe255f8be6631, 0x4e96119e22dedc81), # octave_-9
    (0x0ef68ec68504005e, 0x48b6bf93a2789640), # octave_-8
    (0xf11268128982754f, 0x257a1d670430b0aa), # octave_-7
    (0xe51c98ce7d1de664, 0x5f9478a733040c45), # octave_-6
    (0x6d7b49e7e429850a, 0x2e3063c622a24777), # octave_-5
    (0xbd90d5377ba1b762, 0xc07317d419a7548d), # octave_-4
    (0x53d39c6752dac858, 0xbcd1c5a80ab65b3e), # octave_-3
    (0xb4a24d7a84e7677b, 0x023ff9668e89b5c4), # octave_-2
    (0xdffa22b534c5f608, 0xb9b67517d3665ca9), # octave_-1
    (0xd50708086cef4d7c, 0x6e1651ecc7f43309), # octave_0
]
LACUNA_INI = [1, .5, .25, 1./8, 1./16, 1./32, 1./64, 1./128, 1./256, 1./512,
              1./1024, 1./2048, 1./4096]
PERSIST_INI = [0, 1, 2./3, 4./7, 8./15, 16./31, 32./63, 64./127, 128./255, 256./511]
AMP_INI = [0, 5./6, 10./9, 15./12, 20./15, 25./18, 30./21, 35./24, 40./27, 45./30]

def indexed_lerp(idx, a, b, c):
    idx &= 0xf
    if idx == 0:  return a + b
    if idx == 1:  return -a + b
    if idx == 2:  return a - b
    if idx == 3:  return -a - b
    if idx == 4:  return a + c
    if idx == 5:  return -a + c
    if idx == 6:  return a - c
    if idx == 7:  return -a - c
    if idx == 8:  return b + c
    if idx == 9:  return -b + c
    if idx == 10: return b - c
    if idx == 11: return -b - c
    if idx == 12: return a + b
    if idx == 13: return -b + c
    if idx == 14: return -a + b
    return -b - c

def x_perlin_init(xr):
    a = xr.next_double() * 256.0
    b = xr.next_double() * 256.0
    c = xr.next_double() * 256.0
    idx = list(range(256))
    for i in range(256):
        j = xr.next_int(256 - i) + i
        idx[i], idx[j] = idx[j], idx[i]
    idx.append(idx[0])
    i2 = math.floor(b)
    d2 = b - i2
    h2 = int(i2) & 0xFF
    t2 = d2*d2*d2 * (d2 * (d2*6.0 - 15.0) + 10.0)
    return {'d': idx, 'a': a, 'b': b, 'c': c, 'h2': h2, 'd2': d2, 't2': t2,
            'amp': 1.0, 'lac': 1.0}

def sample_perlin(p, d1, d2, d3):
    if d2 == 0.0:
        d2 = p['d2']; h2 = p['h2']; t2 = p['t2']
    else:
        d2 += p['b']
        i2 = math.floor(d2)
        d2 -= i2
        h2 = int(i2) & 0xFF
        t2 = d2*d2*d2 * (d2 * (d2*6.0 - 15.0) + 10.0)
    d1 += p['a']; d3 += p['c']
    i1 = math.floor(d1); i3 = math.floor(d3)
    d1 -= i1; d3 -= i3
    h1 = int(i1) & 0xFF; h3 = int(i3) & 0xFF
    t1 = d1*d1*d1 * (d1 * (d1*6.0 - 15.0) + 10.0)
    t3 = d3*d3*d3 * (d3 * (d3*6.0 - 15.0) + 10.0)
    idx = p['d']
    a1 = (idx[h1] + h2) & 0xFF
    b1 = (idx[h1 + 1] + h2) & 0xFF
    a2 = (idx[a1] + h3) & 0xFF
    b2 = (idx[b1] + h3) & 0xFF
    a3 = (idx[a1 + 1] + h3) & 0xFF
    b3 = (idx[b1 + 1] + h3) & 0xFF
    l1 = indexed_lerp(idx[a2],     d1,     d2,     d3)
    l2 = indexed_lerp(idx[b2],     d1 - 1, d2,     d3)
    l3 = indexed_lerp(idx[a3],     d1,     d2 - 1, d3)
    l4 = indexed_lerp(idx[b3],     d1 - 1, d2 - 1, d3)
    l5 = indexed_lerp(idx[a2 + 1], d1,     d2,     d3 - 1)
    l6 = indexed_lerp(idx[b2 + 1], d1 - 1, d2,     d3 - 1)
    l7 = indexed_lerp(idx[a3 + 1], d1,     d2 - 1, d3 - 1)
    l8 = indexed_lerp(idx[b3 + 1], d1 - 1, d2 - 1, d3 - 1)
    l1 = l1 + t1 * (l2 - l1); l3 = l3 + t1 * (l4 - l3)
    l5 = l5 + t1 * (l6 - l5); l7 = l7 + t1 * (l8 - l7)
    l1 = l1 + t2 * (l3 - l1); l5 = l5 + t2 * (l7 - l5)
    return l1 + t3 * (l5 - l1)

def sample_octave(o, x, y, z):
    v = 0.0
    for p in o:
        lf = p['lac']
        v += p['amp'] * sample_perlin(p, x * lf, y * lf, z * lf)
    return v

def sample_double_perlin(dp, x, y, z):
    f = 337.0 / 331.0
    v = sample_octave(dp['A'], x, y, z)
    v += sample_octave(dp['B'], x * f, y * f, z * f)
    return v * dp['amplitude']

def x_octave_init(xr, amp, omin, nmax=-1):
    lacuna = LACUNA_INI[-omin]
    persist = PERSIST_INI[len(amp)]
    xlo = xr.next_long(); xhi = xr.next_long()
    octs = []
    for i in range(len(amp)):
        if amp[i] != 0:
            pxr = Xoroshiro()
            pxr.lo = (xlo ^ MD5_OCT[12 + omin + i][0]) & MASK64
            pxr.hi = (xhi ^ MD5_OCT[12 + omin + i][1]) & MASK64
            p = x_perlin_init(pxr)
            p['amp'] = amp[i] * persist
            p['lac'] = lacuna
            octs.append(p)
        lacuna *= 2.0
        persist *= 0.5
    return octs

def x_double_perlin_init(xr, amp, omin):
    A = x_octave_init(xr, amp, omin)
    B = x_octave_init(xr, amp, omin)
    L = len(amp)
    i = L - 1
    while i >= 0 and amp[i] == 0.0:
        L -= 1; i -= 1
    i = 0
    while amp[i] == 0.0:
        L -= 1; i += 1
    return {'A': A, 'B': B, 'amplitude': AMP_INI[L]}

#------------------------------------------------------------------------------
# Climate setup (biomenoise.c init_climate_seed / setBiomeSeed)
#------------------------------------------------------------------------------
NP_TEMP, NP_HUM, NP_CONT, NP_EROS, NP_SHIFT, NP_WEIRD = range(6)

def init_climate_seed(xlo, xhi, large, np):
    pxr = Xoroshiro()
    if np == NP_SHIFT:
        amp = [1, 1, 1, 0]
        pxr.lo = (xlo ^ 0x080518cf6af25384) & MASK64
        pxr.hi = (xhi ^ 0x3f3dfb40a54febd5) & MASK64
        return x_double_perlin_init(pxr, amp, -3)
    if np == NP_TEMP:
        amp = [1.5, 0, 1, 0, 0, 0]
        pxr.lo = (xlo ^ (0x944b0073edf549db if large else 0x5c7e6b29735f0d7f)) & MASK64
        pxr.hi = (xhi ^ (0x4ff44347e9d22b96 if large else 0xf7d86f1bbc734988)) & MASK64
        return x_double_perlin_init(pxr, amp, -12 if large else -10)
    if np == NP_HUM:
        amp = [1, 1, 0, 0, 0, 0]
        pxr.lo = (xlo ^ (0x71b8ab943dbd5301 if large else 0x81bb4d22e8dc168e)) & MASK64
        pxr.hi = (xhi ^ (0xbb63ddcf39ff7a2b if large else 0xf1c8b4bea16303cd)) & MASK64
        return x_double_perlin_init(pxr, amp, -10 if large else -8)
    if np == NP_CONT:
        amp = [1, 1, 2, 2, 2, 1, 1, 1, 1]
        pxr.lo = (xlo ^ (0x9a3f51a113fce8dc if large else 0x83886c9d0ae3a662)) & MASK64
        pxr.hi = (xhi ^ (0xee2dbd157e5dcdad if large else 0xafa638a61b42e8ad)) & MASK64
        return x_double_perlin_init(pxr, amp, -11 if large else -9)
    if np == NP_EROS:
        amp = [1, 1, 0, 1, 1]
        pxr.lo = (xlo ^ (0x8c984b1f8702a951 if large else 0xd02491e6058f6fd8)) & MASK64
        pxr.hi = (xhi ^ (0xead7b1f92bae535f if large else 0x4792512c94c17a80)) & MASK64
        return x_double_perlin_init(pxr, amp, -11 if large else -9)
    if np == NP_WEIRD:
        amp = [1, 2, 1, 0, 0, 0]
        pxr.lo = (xlo ^ 0xefc8ef4d36102b34) & MASK64
        pxr.hi = (xhi ^ 0x1beeeb324a0f24ea) & MASK64
        return x_double_perlin_init(pxr, amp, -7)
    raise AssertionError

def set_biome_seed(seed, large=False):
    xr = Xoroshiro(seed)
    xlo = xr.next_long(); xhi = xr.next_long()
    return [init_climate_seed(xlo, xhi, large, i) for i in range(6)]

#------------------------------------------------------------------------------
# Offset splines (biomenoise.c, float32)
#------------------------------------------------------------------------------
SP_CONT, SP_EROS, SP_RIDGES, SP_WEIRD = 0, 1, 2, 3

def get_offset_value(weirdness, continentalness):
    f0 = f32(1.0 - f32(f32(1.0 - continentalness) * 0.5))
    f1 = f32(0.5 * f32(1.0 - continentalness))
    f2 = f32(f32(weirdness + 1.17) * 0.46082947)
    off = f32(f32(f2 * f0) - f1)
    if weirdness < -0.7:
        return off if off > f32(-0.2222) else f32(-0.2222)
    return off if off > 0 else 0.0

def build_splines():
    # returns (splines_list, root) with FixSpline as ('fix', val)
    splines = []
    def spline(typ):
        s = {'typ': typ, 'pts': []}
        splines.append(s)
        return s
    def fix(v):
        return ('fix', f32(v))
    def add(sp, loc, val, der):
        sp['pts'].append((f32(loc), val, f32(der)))
    def create_spline_38219(f, bl):
        sp = spline(SP_RIDGES)
        i = get_offset_value(-1.0, f)
        k = get_offset_value(1.0, f)
        l = f32(1.0 - f32(f32(1.0 - f) * 0.5))
        u = f32(0.5 * f32(1.0 - f))
        l = f32(f32(u / f32(0.46082947 * l)) - 1.17)
        if f32(-0.65) < l < 1.0:
            u = get_offset_value(-0.65, f)
            p = get_offset_value(-0.75, f)
            q = f32(f32(p - i) * 4.0)
            r = get_offset_value(l, f)
            s = f32(f32(k - r) / f32(1.0 - l))
            add(sp, -1.0, fix(i), q)
            add(sp, -0.75, fix(p), 0.0)
            add(sp, -0.65, fix(u), 0.0)
            add(sp, f32(l - 0.01), fix(r), 0.0)
            add(sp, l, fix(r), s)
            add(sp, 1.0, fix(k), s)
        else:
            u = f32(f32(k - i) * 0.5)
            if bl:
                iv = f32(i if i > 0.2 else 0.2)
                add(sp, -1.0, fix(iv), 0.0)
                add(sp, 0.0, fix(f32(i + 0.5 * (k - i))), u)  # lerp(0.5F, i, k)
            else:
                add(sp, -1.0, fix(i), u)
            add(sp, 1.0, fix(k), u)
        return sp
    def create_flat_offset(f, g, h, i, j, k):
        sp = spline(SP_RIDGES)
        l = f32(0.5 * f32(g - f))
        if l < k: l = k
        m = f32(5.0 * f32(h - g))
        add(sp, -1.0, fix(f), l)
        add(sp, -0.4, fix(g), f32(l if l < m else m))
        add(sp, 0.0, fix(h), m)
        add(sp, 0.4, fix(i), f32(2.0 * f32(i - h)))
        add(sp, 1.0, fix(j), f32(0.7 * f32(j - i)))
        return sp
    def create_land(f, g, h, i, j, k, bl):
        sp1 = create_spline_38219(f32(0.6 + i * (1.5 - 0.6)), bl)
        sp2 = create_spline_38219(f32(0.6 + i * (1.0 - 0.6)), bl)
        sp3 = create_spline_38219(i, bl)
        ih = f32(0.5 * i)
        sp4 = create_flat_offset(f32(f - 0.15), ih, ih, ih, f32(i * 0.6), 0.5)
        sp5 = create_flat_offset(f, f32(j * i), f32(g * i), ih, f32(i * 0.6), 0.5)
        sp6 = create_flat_offset(f, j, j, g, h, 0.5)
        sp7 = create_flat_offset(f, j, j, g, h, 0.5)
        sp8 = spline(SP_RIDGES)
        add(sp8, -1.0, fix(f), 0.0)
        add(sp8, -0.4, sp6, 0.0)
        add(sp8, 0.0, fix(f32(h + 0.07)), 0.0)
        sp9 = create_flat_offset(-0.02, k, k, g, h, 0.0)
        sp = spline(SP_EROS)
        add(sp, -0.85, sp1, 0.0)
        add(sp, -0.7, sp2, 0.0)
        add(sp, -0.4, sp3, 0.0)
        add(sp, -0.35, sp4, 0.0)
        add(sp, -0.1, sp5, 0.0)
        add(sp, 0.2, sp6, 0.0)
        if bl:
            add(sp, 0.4, sp7, 0.0)
            add(sp, 0.45, sp8, 0.0)
            add(sp, 0.55, sp8, 0.0)
            add(sp, 0.58, sp7, 0.0)
        add(sp, 0.7, sp9, 0.0)
        return sp

    root = spline(SP_CONT)
    sp1 = create_land(-0.15, 0.00, 0.0, 0.1, 0.00, -0.03, False)
    sp2 = create_land(-0.10, 0.03, 0.1, 0.1, 0.01, -0.03, False)
    sp3 = create_land(-0.10, 0.03, 0.1, 0.7, 0.01, -0.03, True)
    sp4 = create_land(-0.05, 0.03, 0.1, 1.0, 0.01, 0.01, True)
    add(root, -1.10, fix(0.044), 0.0)
    add(root, -1.02, fix(-0.2222), 0.0)
    add(root, -0.51, fix(-0.2222), 0.0)
    add(root, -0.44, fix(-0.12), 0.0)
    add(root, -0.18, fix(-0.12), 0.0)
    add(root, -0.16, sp1, 0.0)
    add(root, -0.15, sp1, 0.0)
    add(root, -0.10, sp2, 0.0)
    add(root, 0.25, sp3, 0.0)
    add(root, 1.00, sp4, 0.0)
    return root

def get_spline(sp, vals):
    if isinstance(sp, tuple):  # fix
        return sp[1]
    f = vals[sp['typ']]
    pts = sp['pts']
    i = 0
    for i in range(len(pts)):
        if pts[i][0] >= f:
            break
    else:
        i = len(pts)
    if i == 0 or i == len(pts):
        if i: i -= 1
        loc, val, der = pts[i]
        v = get_spline(val, vals)
        return f32(v + f32(der * f32(f - loc)))
    g, sp1, der_l = pts[i - 1]
    h, sp2, der_r = pts[i]
    k = f32(f32(f - g) / f32(h - g))
    n = get_spline(sp1, vals)
    o = get_spline(sp2, vals)
    p = f32(f32(der_l * f32(h - g)) - f32(o - n))
    q = f32(f32(-der_r * f32(h - g)) + f32(o - n))
    kf = f32(k * f32(1.0 - k))
    # C: float r = lerp(k,n,o) + k*(1.0F-k)*lerp(k,p,q); lerps run in double
    a1 = n + k * (o - n)
    a2 = p + k * (q - p)
    return f32(a1 + kf * a2)

#------------------------------------------------------------------------------
# btree (tables/*.h + biomenoise.c get_np_dist/get_resulting_node)
#------------------------------------------------------------------------------
def load_btree(tag):
    txt = (TABLES / f"btree{tag}.h").read_text()
    order = int(re.search(rf"enum \{{ btree{tag}_order = (\d+) \}};", txt).group(1))
    steps = [int(x) for x in re.search(
        rf"btree{tag}_steps\[\] = \{{([^;]*)\}};", txt).group(1).replace("\n", " ").split(",") if x.strip()]
    pm = re.search(rf"btree{tag}_param\[\]\[2\] =\s*\{{(.*?)\n\}};", txt, re.S)
    # strip // comments first: line comments like "// 00-03" contain digits!
    pm_clean = re.sub(r"//[^\n]*", "", pm.group(1))
    param = [int(x) for x in re.findall(r"-?\d+", pm_clean)]
    nm = re.search(rf"btree{tag}_nodes\[\] =\s*\{{(.*?)\n\}};", txt, re.S)
    nm_clean = re.sub(r"//[^\n]*", "", nm.group(1))
    nodes = [int(x, 16) for x in re.findall(r"0x([0-9a-fA-F]{16})", nm_clean)]
    return {'steps': steps, 'param': param, 'nodes': nodes, 'order': order,
            'len': len(nodes)}

def get_np_dist(np, bt, idx):
    node = bt['nodes'][idx]
    ds = 0
    for i in range(6):
        pi = (node >> (8 * i)) & 0xFF
        a = (np[i] - bt['param'][2 * pi + 1]) & MASK64
        b = (bt['param'][2 * pi] - np[i]) & MASK64
        if a >> 63: a = 0        # (int64_t)a > 0 ? a : ...
        sa = a if not (a >> 63) else 0
        # signed interpretation
        sa = a - MASK64 - 1 if a >> 63 else a
        sb = b - MASK64 - 1 if b >> 63 else b
        d = sa if sa > 0 else (sb if sb > 0 else 0)
        ds += d * d
    return ds

def get_resulting_node(np, bt, idx, alt, ds, depth):
    if bt['steps'][depth] == 0:
        return idx
    while True:
        step = bt['steps'][depth]
        depth += 1
        if idx + step < bt['len']:
            break
    node = bt['nodes'][idx]
    inner = (node >> 48) & 0xFFFF
    leaf = alt
    for _ in range(bt['order']):
        ds_inner = get_np_dist(np, bt, inner)
        if ds_inner < ds:
            leaf2 = get_resulting_node(np, bt, inner, leaf, ds, depth)
            ds_leaf2 = ds_inner if inner == leaf2 else get_np_dist(np, bt, leaf2)
            if ds_leaf2 < ds:
                ds = ds_leaf2
                leaf = leaf2
        inner += step
        if inner >= bt['len']:
            break
    return leaf

BTS = {}

def climate_to_biome(ver, np):
    if ver not in BTS:
        tag = {18: '18', 192: '192', 19: '19', 20: '20', 21: '21wd'}[ver]
        BTS[ver] = load_btree(tag)
    bt = BTS[ver]
    idx = get_resulting_node(np, bt, 0, 0, MASK64, 0)
    return (bt['nodes'][idx] >> 48) & 0xFF

#------------------------------------------------------------------------------
# sampleBiomeNoise (biomenoise.c) with float32 emulation
#------------------------------------------------------------------------------
def sample_biome_noise(climate, root, x, y, z, ver):
    px = float(x); pz = float(z)
    px += sample_double_perlin(climate[NP_SHIFT], x, 0, z) * 4.0
    pz += sample_double_perlin(climate[NP_SHIFT], z, x, 0) * 4.0
    c = f32(sample_double_perlin(climate[NP_CONT], px, 0, pz))
    e = f32(sample_double_perlin(climate[NP_EROS], px, 0, pz))
    w = f32(sample_double_perlin(climate[NP_WEIRD], px, 0, pz))
    ridge = f32(-3.0 * f32(abs(f32(abs(w) - 0.6666667)) - 0.33333334))
    off = f32(get_spline(root, [c, e, ridge, w]) + f32(0.015))
    d = f32(1.0 - (y * 4) / 128.0 - 83.0 / 160.0 + off)
    t = f32(sample_double_perlin(climate[NP_TEMP], px, 0, pz))
    h = f32(sample_double_perlin(climate[NP_HUM], px, 0, pz))
    np = [int(f32(10000.0 * v)) for v in (t, h, c, e, d, w)]
    return climate_to_biome(ver, np), np

#------------------------------------------------------------------------------
# Golden test (tests.c getRef bits=6 scale=4)
#------------------------------------------------------------------------------
def hash32(x):
    x &= MASK32
    x ^= x >> 15; x = (x * 0xd168aaad) & MASK32
    x ^= x >> 15; x = (x * 0xaf723597) & MASK32
    x ^= x >> 15
    return x

def golden(ver, dump=None):
    root = build_splines()
    hsh = 0
    r = 32
    lines = []
    for x in range(-r, r):
        for z in range(-r, r):
            s = ((z << 6) ^ x) & MASK32
            if s >= 1 << 31: s -= 1 << 32   # (int64_t)(int)s
            climate = set_biome_seed(s)
            y = ((hash32(s & MASK32) & 0x7fffffff) % 384 - 64) >> 2
            # y computed on (int)s; hash32 takes uint32 of s
            sid = s & MASK32
            y = ((hash32(sid) & 0x7fffffff) % 384 - 64) >> 2
            idb, np = sample_biome_noise(climate, root, x, y, z, ver)
            hsh ^= hash32((sid ^ ((idb << 12) & MASK32)) & MASK32)
            if dump is not None:
                lines.append((x, z, idb, np))
    return hsh, lines

if __name__ == "__main__":
    ver = sys.argv[1] if len(sys.argv) > 1 else "18"
    ver = int(ver)
    hsh, lines = golden(ver, dump=True)
    print(f"MC 1.{ver}: hash = {hsh:08x}")
    import json
    out = pathlib.Path(__file__).parent / f"ref_ids_{ver}.txt"
    with open(out, "w") as f:
        for x, z, idb, np in lines:
            f.write(f"{x} {z} {idb} {np}\n")
    print(f"ids written to {out.name} ({len(lines)} rows)")
