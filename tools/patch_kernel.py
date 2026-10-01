#!/usr/bin/env python3
"""v2.1 内核 float 化补丁: Intel 消费级 GPU 无 FP64, 噪声内部转 float, 振幅/累加保持 double。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. 删除内核中未使用的 Xoroshiro 主机随机段 (状态由主机初始化上传)
start = src.index("        // 蘑菇岛 GPU 采样内核")
xr_start = src.index("        typedef struct { ulong lo, hi; } Xr;", start)
xr_end = src.index("        // ---------- 群系状态:", start)
src = src[:xr_start] + src[xr_end:]

# 2. PState 双精度数组改 float
old = """            __global const uchar*  D;    // [nP*257] 置换表
            __global const double* A; __global const double* B; __global const double* C;
            __global const double* D2; __global const double* T2;
            __global const double* AMP; __global const double* LAC;
            __global const int*    H2;"""
new = """            __global const uchar*  D;    // [nP*257] 置换表
            __global const float*  A; __global const float* B; __global const float* C;
            __global const float*  D2; __global const float* T2;
            __global const double* AMP; __global const double* LAC;
            __global const int*    H2;"""
assert old in src, "PState"
src = src.replace(old, new)

# 3. sample_perlin 改 float 内部
old = """        double sample_perlin(const PState* ps, int p, double d1, double d2, double d3) {
            int base = p * 257;
            int h1, h2, h3;
            double t1, t2, t3;
            __global const uchar* idx = ps->D + base;
            if (d2 == 0.0) {
                d2 = ps->D2[p]; h2 = ps->H2[p]; t2 = ps->T2[p];
            } else {
                d2 += ps->B[p];
                double i2 = floor(d2);
                d2 -= i2;
                h2 = ((int)i2) & 0xFF;
                t2 = d2*d2*d2 * (d2 * (d2*6.0 - 15.0) + 10.0);
            }
            d1 += ps->A[p];
            d3 += ps->C[p];
            double i1 = floor(d1), i3 = floor(d3);
            d1 -= i1; d3 -= i3;
            h1 = ((int)i1) & 0xFF;
            h3 = ((int)i3) & 0xFF;
            t1 = d1*d1*d1 * (d1 * (d1*6.0 - 15.0) + 10.0);
            t3 = d3*d3*d3 * (d3 * (d3*6.0 - 15.0) + 10.0);"""
new = """        // 注意: 本核为 float 近似 (Intel 消费级 GPU 无 FP64); 振幅/累加仍为 double
        float sample_perlin(const PState* ps, int p, float d1, float d2, float d3) {
            int base = p * 257;
            int h1, h2, h3;
            float t1, t2, t3;
            __global const uchar* idx = ps->D + base;
            if (d2 == 0.0f) {
                d2 = ps->D2[p]; h2 = ps->H2[p]; t2 = ps->T2[p];
            } else {
                d2 += ps->B[p];
                float i2 = floor(d2);
                d2 -= i2;
                h2 = ((int)i2) & 0xFF;
                t2 = d2*d2*d2 * (d2 * (d2*6.0f - 15.0f) + 10.0f);
            }
            d1 += ps->A[p];
            d3 += ps->C[p];
            float i1 = floor(d1), i3 = floor(d3);
            d1 -= i1; d3 -= i3;
            h1 = ((int)i1) & 0xFF;
            h3 = ((int)i3) & 0xFF;
            t1 = d1*d1*d1 * (d1 * (d1*6.0f - 15.0f) + 10.0f);
            t3 = d3*d3*d3 * (d3 * (d3*6.0f - 15.0f) + 10.0f);"""
assert old in src, "sample_perlin head"
src = src.replace(old, new)

old = """            double l1 = indexed_lerp(idx[a2],     d1,     d2,     d3);
            double l2 = indexed_lerp(idx[b2],     d1 - 1, d2,     d3);
            double l3 = indexed_lerp(idx[a3],     d1,     d2 - 1, d3);
            double l4 = indexed_lerp(idx[b3],     d1 - 1, d2 - 1, d3);
            double l5 = indexed_lerp(idx[a2 + 1], d1,     d2,     d3 - 1);
            double l6 = indexed_lerp(idx[b2 + 1], d1 - 1, d2,     d3 - 1);
            double l7 = indexed_lerp(idx[a3 + 1], d1,     d2 - 1, d3 - 1);
            double l8 = indexed_lerp(idx[b3 + 1], d1 - 1, d2 - 1, d3 - 1);"""
new = """            float l1 = indexed_lerp(idx[a2],     d1,     d2,     d3);
            float l2 = indexed_lerp(idx[b2],     d1 - 1, d2,     d3);
            float l3 = indexed_lerp(idx[a3],     d1,     d2 - 1, d3);
            float l4 = indexed_lerp(idx[b3],     d1 - 1, d2 - 1, d3);
            float l5 = indexed_lerp(idx[a2 + 1], d1,     d2,     d3 - 1);
            float l6 = indexed_lerp(idx[b2 + 1], d1 - 1, d2,     d3 - 1);
            float l7 = indexed_lerp(idx[a3 + 1], d1,     d2 - 1, d3 - 1);
            float l8 = indexed_lerp(idx[b3 + 1], d1 - 1, d2 - 1, d3 - 1);"""
assert old in src, "sample_perlin lerps"
src = src.replace(old, new)

# 4. sample_octave: perlin float 结果转 double, 用 double 振幅累加
old = """        double sample_octave(const PState* ps, int off, int cnt, double x, double y, double z) {
            double v = 0.0;
            for (int k = 0; k < cnt; k++) {
                int p = off + k;
                double lf = ps->LAC[p];
                v += ps->AMP[p] * sample_perlin(ps, p, x * lf, y * lf, z * lf);
            }
            return v;
        }"""
new = """        double sample_octave(const PState* ps, int off, int cnt, double x, double y, double z) {
            double v = 0.0;
            for (int k = 0; k < cnt; k++) {
                int p = off + k;
                double lf = ps->LAC[p];
                v += ps->AMP[p] * (double)sample_perlin(ps, p,
                        (float)(x * lf), (float)(y * lf), (float)(z * lf));
            }
            return v;
        }"""
assert old in src, "sample_octave"
src = src.replace(old, new)

# 5. 主机侧序列化: a/b/c/d2/t2 转 float 数组
old = """            byte[] sD = new byte[nP * 257];
            double[] sA = new double[nP], sB = new double[nP], sC = new double[nP];
            double[] sD2 = new double[nP], sT2 = new double[nP];
            double[] sAMP = new double[nP], sLAC = new double[nP];
            int[] sH2 = new int[nP];
            for (int p = 0; p < nP; p++) {
                Perlin pl = perlins.get(p);
                for (int k = 0; k < 257; k++) sD[p * 257 + k] = (byte) pl.d[k];
                sA[p] = pl.a; sB[p] = pl.b; sC[p] = pl.c;
                sD2[p] = pl.d2; sT2[p] = pl.t2;
                sAMP[p] = pl.amplitude; sLAC[p] = pl.lacunarity;
                sH2[p] = pl.h2;
            }"""
new = """            byte[] sD = new byte[nP * 257];
            float[] sA = new float[nP], sB = new float[nP], sC = new float[nP];
            float[] sD2 = new float[nP], sT2 = new float[nP];
            double[] sAMP = new double[nP], sLAC = new double[nP];
            int[] sH2 = new int[nP];
            for (int p = 0; p < nP; p++) {
                Perlin pl = perlins.get(p);
                for (int k = 0; k < 257; k++) sD[p * 257 + k] = (byte) pl.d[k];
                sA[p] = (float) pl.a; sB[p] = (float) pl.b; sC[p] = (float) pl.c;
                sD2[p] = (float) pl.d2; sT2[p] = (float) pl.t2;
                sAMP[p] = pl.amplitude; sLAC[p] = pl.lacunarity;
                sH2[p] = pl.h2;
            }"""
assert old in src, "serialize"
src = src.replace(old, new)

# 6. 缓冲大小: A/B/C/D2/T2 改 4 字节
old = """            memA = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memB = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memD2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memT2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);"""
new = """            memA = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memB = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memD2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memT2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);"""
assert old in src, "buffers"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patched ok")
