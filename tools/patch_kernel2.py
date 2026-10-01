#!/usr/bin/env python3
"""v2.1 内核完全 float 化补丁 (Intel 消费级 GPU 无任何 FP64 支持)。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. PState 全 float
old = """        typedef struct {
            __global const uchar*  D;    // [nP*257] 置换表
            __global const float*  A; __global const float* B; __global const float* C;
            __global const float*  D2; __global const float* T2;
            __global const double* AMP; __global const double* LAC;
            __global const int*    H2;
        } PState;"""
new = """        typedef struct {
            __global const uchar*  D;    // [nP*257] 置换表
            __global const float*  A; __global const float* B; __global const float* C;
            __global const float*  D2; __global const float* T2;
            __global const float*  AMP; __global const float* LAC;
            __global const int*    H2;
        } PState;"""
assert old in src, "PState"
src = src.replace(old, new)

# 2. indexed_lerp float
old = """        double indexed_lerp(int idx, double a, double b, double c) {"""
new = """        float indexed_lerp(int idx, float a, float b, float c) {"""
assert old in src, "indexed_lerp"
src = src.replace(old, new)
src = src.replace("""
        double indexed_lerp_d(int idx, double a, double b, double c) { return indexed_lerp(idx, a, b, c); }""", "")

# 3. sample_octave float
old = """        double sample_octave(const PState* ps, int off, int cnt, double x, double y, double z) {
            double v = 0.0;
            for (int k = 0; k < cnt; k++) {
                int p = off + k;
                double lf = ps->LAC[p];
                v += ps->AMP[p] * (double)sample_perlin(ps, p,
                        (float)(x * lf), (float)(y * lf), (float)(z * lf));
            }
            return v;
        }"""
new = """        float sample_octave(const PState* ps, int off, int cnt, float x, float y, float z) {
            float v = 0.0f;
            for (int k = 0; k < cnt; k++) {
                int p = off + k;
                float lf = ps->LAC[p];
                v += ps->AMP[p] * sample_perlin(ps, p, x * lf, y * lf, z * lf);
            }
            return v;
        }"""
assert old in src, "sample_octave"
src = src.replace(old, new)

# 4. sample_double_perlin float
old = """        __constant double kDPF = 337.0 / 331.0;

        double sample_double_perlin(const PState* ps, int ch, double x, double y, double z,
                __global const int* OffA, __global const int* OffB,
                __global const int* NA, __global const int* NB,
                __global const double* CAMP) {
            double v = sample_octave(ps, OffA[ch], NA[ch], x, y, z);
            v += sample_octave(ps, OffB[ch], NB[ch], x * kDPF, y * kDPF, z * kDPF);
            return v * CAMP[ch];
        }"""
new = """        __constant float kDPF = 337.0f / 331.0f;

        float sample_double_perlin(const PState* ps, int ch, float x, float y, float z,
                __global const int* OffA, __global const int* OffB,
                __global const int* NA, __global const int* NB,
                __global const float* CAMP) {
            float v = sample_octave(ps, OffA[ch], NA[ch], x, y, z);
            v += sample_octave(ps, OffB[ch], NB[ch], x * kDPF, y * kDPF, z * kDPF);
            return v * CAMP[ch];
        }"""
assert old in src, "sample_double_perlin"
src = src.replace(old, new)

# 5. sample_biome float 化
old = """        int sample_biome(const PState* ps, const SplineBuf* sb, int root,
                const BTreeBuf* bt, long* np, int x, int y, int z) {
            float t, h, c, e, d, w;
            double px = (double)x, pz = (double)z;
            px += sample_double_perlin(ps, 4, x, 0, z) * 4.0;
            pz += sample_double_perlin(ps, 4, z, x, 0) * 4.0;
            c = (float)sample_double_perlin(ps, 2, px, 0, pz);
            e = (float)sample_double_perlin(ps, 3, px, 0, pz);
            w = (float)sample_double_perlin(ps, 5, px, 0, pz);
            {
                float vals[4];
                vals[0] = c; vals[1] = e;
                vals[2] = -3.0f * (fabs(fabs(w) - 0.6666667f) - 0.33333334f);
                vals[3] = w;
                double off = spline_eval(root, vals, sb) + 0.015f;
                d = (float)(1.0 - (y * 4) / 128.0 - 83.0 / 160.0 + off);
            }
            t = (float)sample_double_perlin(ps, 0, px, 0, pz);
            h = (float)sample_double_perlin(ps, 1, px, 0, pz);
            np[0] = (long)(10000.0f * t);"""
new = """        int sample_biome(const PState* ps, const SplineBuf* sb, int root,
                const BTreeBuf* bt, long* np, int x, int y, int z) {
            float t, h, c, e, d, w;
            float px = (float)x, pz = (float)z;
            px += sample_double_perlin(ps, 4, x, 0, z) * 4.0f;
            pz += sample_double_perlin(ps, 4, z, x, 0) * 4.0f;
            c = sample_double_perlin(ps, 2, px, 0, pz);
            e = sample_double_perlin(ps, 3, px, 0, pz);
            w = sample_double_perlin(ps, 5, px, 0, pz);
            {
                float vals[4];
                vals[0] = c; vals[1] = e;
                vals[2] = -3.0f * (fabs(fabs(w) - 0.6666667f) - 0.33333334f);
                vals[3] = w;
                float off = spline_eval(root, vals, sb) + 0.015f;
                d = 1.0f - (float)(y * 4) / 128.0f - 83.0f / 160.0f + off;
            }
            t = sample_double_perlin(ps, 0, px, 0, pz);
            h = sample_double_perlin(ps, 1, px, 0, pz);
            np[0] = (long)(10000.0f * t);"""
assert old in src, "sample_biome"
src = src.replace(old, new)

# 6. 主机侧: AMP/LAC/CAMP 也转 float
old = """            double[] sAMP = new double[nP], sLAC = new double[nP];
            int[] sH2 = new int[nP];"""
new = """            float[] sAMP = new float[nP], sLAC = new float[nP];
            int[] sH2 = new int[nP];"""
assert old in src, "amp arrays"
src = src.replace(old, new)
src = src.replace("                sAMP[p] = pl.amplitude; sLAC[p] = pl.lacunarity;",
                  "                sAMP[p] = (float) pl.amplitude; sLAC[p] = (float) pl.lacunarity;")
old = """            int[] offA = new int[6], offB = new int[6], nA = new int[6], nB = new int[6];
            double[] camp = new double[6];"""
new = """            int[] offA = new int[6], offB = new int[6], nA = new int[6], nB = new int[6];
            float[] camp = new float[6];"""
assert old in src, "camp"
src = src.replace(old, new)
src = src.replace("                camp[ch] = dp.amplitude;",
                  "                camp[ch] = (float) dp.amplitude;")

# 7. 缓冲大小: AMP/LAC/CAMP 8->4
old = """            memPAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memPLAC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memCAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 8L, null, null);"""
new = """            memPAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memPLAC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memCAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 4L, null, null);"""
assert old in src, "amp buffers"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patched ok")
