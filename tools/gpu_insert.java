    //==========================================================================
    //              GPU (OpenCL) 扫描后端 — 内核为本项目 Java 实现的移植
    //==========================================================================
    static final String GPU_KERNEL = """
        // 蘑菇岛 GPU 采样内核 (OpenCL C) — 移植自已通过 cubiomes 黄金验证的 Java 实现
        typedef struct { ulong lo, hi; } Xr;

        __constant ulong kXL = 0x9e3779b97f4a7c15UL, kXH = 0x6a09e667f3bcc909UL;
        __constant ulong kXA = 0xbf58476d1ce4e5b9UL, kXB = 0x94d049bb133111ebUL;

        void xr_set(Xr* s, ulong v) {
            ulong l = v ^ kXH;
            ulong h = l + kXL;
            l = (l ^ (l >> 30)) * kXA;
            h = (h ^ (h >> 30)) * kXA;
            l = (l ^ (l >> 27)) * kXB;
            h = (h ^ (h >> 27)) * kXB;
            s->lo = l ^ (l >> 31);
            s->hi = h ^ (h >> 31);
        }
        ulong xr_next(Xr* s) {
            ulong l = s->lo, h = s->hi;
            ulong n = (((l + h) << 17) | ((l + h) >> 47)) + l;
            h ^= l;
            s->lo = ((l << 49) | (l >> 15)) ^ h ^ (h << 21);
            s->hi = (h << 28) | (h >> 36);
            return n;
        }
        int xr_int(Xr* s, uint n) {
            ulong r = (xr_next(s) & 0xFFFFFFFFUL) * (ulong)n;
            if ((uint)r < n) {
                uint lim = (uint)(((1UL << 32) - (ulong)n) % (ulong)n);
                while ((uint)r < lim) r = (xr_next(s) & 0xFFFFFFFFUL) * (ulong)n;
            }
            return (int)(r >> 32);
        }
        double xr_double(Xr* s) {
            return (double)(xr_next(s) >> 11) * 1.1102230246251565E-16;
        }

        // ---------- 群系状态: 由主机端(Java, 已过黄金自检)序列化上传 ----------
        typedef struct {
            __global const uchar*  D;    // [nP*257] 置换表
            __global const double* A; __global const double* B; __global const double* C;
            __global const double* D2; __global const double* T2;
            __global const double* AMP; __global const double* LAC;
            __global const int*    H2;
        } PState;

        double indexed_lerp(int idx, double a, double b, double c) {
            int k = idx & 0xf;
            if (k == 0)  return a + b;
            if (k == 1)  return -a + b;
            if (k == 2)  return a - b;
            if (k == 3)  return -a - b;
            if (k == 4)  return a + c;
            if (k == 5)  return -a + c;
            if (k == 6)  return a - c;
            if (k == 7)  return -a - c;
            if (k == 8)  return b + c;
            if (k == 9)  return -b + c;
            if (k == 10) return b - c;
            if (k == 11) return -b - c;
            if (k == 12) return a + b;
            if (k == 13) return -b + c;
            if (k == 14) return -a + b;
            return -b - c;
        }

        double sample_perlin(const PState* ps, int p, double d1, double d2, double d3) {
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
            t3 = d3*d3*d3 * (d3 * (d3*6.0 - 15.0) + 10.0);
            int a1 = (idx[h1]     + h2) & 0xFF;
            int b1 = (idx[h1 + 1] + h2) & 0xFF;
            int a2 = (idx[a1]     + h3) & 0xFF;
            int b2 = (idx[b1]     + h3) & 0xFF;
            int a3 = (idx[a1 + 1] + h3) & 0xFF;
            int b3 = (idx[b1 + 1] + h3) & 0xFF;
            double l1 = indexed_lerp(idx[a2],     d1,     d2,     d3);
            double l2 = indexed_lerp(idx[b2],     d1 - 1, d2,     d3);
            double l3 = indexed_lerp(idx[a3],     d1,     d2 - 1, d3);
            double l4 = indexed_lerp(idx[b3],     d1 - 1, d2 - 1, d3);
            double l5 = indexed_lerp(idx[a2 + 1], d1,     d2,     d3 - 1);
            double l6 = indexed_lerp(idx[b2 + 1], d1 - 1, d2,     d3 - 1);
            double l7 = indexed_lerp(idx[a3 + 1], d1,     d2 - 1, d3 - 1);
            double l8 = indexed_lerp(idx[b3 + 1], d1 - 1, d2 - 1, d3 - 1);
            l1 = l1 + t1 * (l2 - l1); l3 = l3 + t1 * (l4 - l3);
            l5 = l5 + t1 * (l6 - l5); l7 = l7 + t1 * (l8 - l7);
            l1 = l1 + t2 * (l3 - l1); l5 = l5 + t2 * (l7 - l5);
            return l1 + t3 * (l5 - l1);
        }

        double sample_octave(const PState* ps, int off, int cnt, double x, double y, double z) {
            double v = 0.0;
            for (int k = 0; k < cnt; k++) {
                int p = off + k;
                double lf = ps->LAC[p];
                v += ps->AMP[p] * sample_perlin(ps, p, x * lf, y * lf, z * lf);
            }
            return v;
        }

        __constant double kDPF = 337.0 / 331.0;

        double sample_double_perlin(const PState* ps, int ch, double x, double y, double z,
                __global const int* OffA, __global const int* OffB,
                __global const int* NA, __global const int* NB,
                __global const double* CAMP) {
            double v = sample_octave(ps, OffA[ch], NA[ch], x, y, z);
            v += sample_octave(ps, OffB[ch], NB[ch], x * kDPF, y * kDPF, z * kDPF);
            return v * CAMP[ch];
        }

        // ---------- 气候通道编号 (与 Java 一致) ----------
        // 0 温度 1 湿度 2 大陆性 3 侵蚀 4 偏移 5 奇异性

        // ---------- 偏移样条 (主机展平上传) ----------
        typedef struct {
            __global const int*   Typ; __global const int*   Len;
            __global const float* Val; __global const float* Loc;
            __global const float* Der; __global const int*   Child;
        } SplineBuf;

        float spline_eval(int root, const float* vals, const SplineBuf* sp) {
            // 递归转显式栈 (树深 <= 5)
            int   fNode[8]; int fStage[8]; int fMode[8]; int fI[8];
            float fF[8], fG[8], fH[8], fK[8], fL[8], fM[8], fN[8];
            int spT = 1;
            float res = 0.0f;
            fNode[0] = root; fStage[0] = 0; fMode[0] = 0;
            while (spT > 0) {
                int top = spT - 1;
                int node = fNode[top];
                if (sp->Len[node] == 1) {
                    res = sp->Val[node];
                    spT--;
                    if (spT > 0) fStage[spT-1]++;
                    continue;
                }
                if (fStage[top] == 0) {
                    float f = vals[sp->Typ[node]];
                    int i = 0;
                    for (i = 0; i < sp->Len[node]; i++)
                        if (sp->Loc[node*12 + i] >= f) break;
                    if (i == 0 || i == sp->Len[node]) {
                        if (i != 0) i--;
                        fI[top] = i; fF[top] = f; fMode[top] = 0; fStage[top] = 1;
                        fNode[spT] = sp->Child[node*12 + i]; fStage[spT] = 0; spT++;
                    } else {
                        float g = sp->Loc[node*12 + i - 1], h = sp->Loc[node*12 + i];
                        fF[top] = f; fI[top] = i; fG[top] = g; fH[top] = h;
                        fK[top] = (f - g) / (h - g);
                        fL[top] = sp->Der[node*12 + i - 1];
                        fM[top] = sp->Der[node*12 + i];
                        fMode[top] = 1; fStage[top] = 2;
                        fNode[spT] = sp->Child[node*12 + i - 1]; fStage[spT] = 0; spT++;
                    }
                } else if (fStage[top] == 1) {
                    float v = res;
                    res = v + sp->Der[node*12 + fI[top]] * (fF[top] - sp->Loc[node*12 + fI[top]]);
                    spT--;
                    if (spT > 0) fStage[spT-1]++;
                } else if (fStage[top] == 2) {
                    fN[top] = res;
                    fStage[top] = 3;
                    fNode[spT] = sp->Child[node*12 + fI[top]]; fStage[spT] = 0; spT++;
                } else {
                    float n = fN[top], o = res;
                    float p = fL[top] * (fH[top] - fG[top]) - (o - n);
                    float q = -fM[top] * (fH[top] - fG[top]) + (o - n);
                    float kf = fK[top] * (1.0f - fK[top]);
                    double r = ((double)n + (double)fK[top] * ((double)o - (double)n))
                             + (double)kf * ((double)p + (double)fK[top] * ((double)q - (double)p));
                    res = (float)r;
                    spT--;
                    if (spT > 0) fStage[spT-1]++;
                }
            }
            return res;
        }

        // ---------- 气候 -> 群系 btree (递归转显式栈) ----------
        typedef struct {
            __global const int*   Steps; __global const int*   Param;
            __global const ulong* Nodes;
            int Order; int Len;
        } BTreeBuf;

        long np_dist(const long* np, const BTreeBuf* bt, int idx) {
            ulong node = bt->Nodes[idx];
            ulong ds = 0;
            for (int i = 0; i < 6; i++) {
                int pi = (int)((node >> (8 * i)) & 0xFFUL);
                long a = np[i] - (long)bt->Param[2 * pi + 1];
                long b = (long)bt->Param[2 * pi] - np[i];
                long d = a > 0 ? a : (b > 0 ? b : 0);
                ds += (ulong)(d * d);
            }
            return (long)ds;
        }

        int btree_biome(const long* np, const BTreeBuf* bt) {
            int   fIdx[10]; int fAlt[10]; int fDepth[10]; int fStep[10];
            int   fInner[10]; int fLeaf[10]; int fI[10]; int fStage[10];
            long  fDs[10]; long fDsInner[10];
            int spT = 1;
            int res = 0;
            fIdx[0] = 0; fAlt[0] = 0; fDs[0] = -1L; fDepth[0] = 0; fStage[0] = 0;
            while (spT > 0) {
                int top = spT - 1;
                if (fStage[top] == 0) {
                    if (bt->Steps[fDepth[top]] == 0) {
                        res = fIdx[top];
                        spT--;
                        if (spT > 0) fStage[spT-1] = 2;
                        continue;
                    }
                    int step;
                    do {
                        step = bt->Steps[fDepth[top]];
                        fDepth[top]++;
                    } while (fIdx[top] + step >= bt->Len);
                    fStep[top] = step;
                    fInner[top] = (int)((bt->Nodes[fIdx[top]] >> 48) & 0xFFFFUL);
                    fLeaf[top] = fAlt[top];
                    fI[top] = 0;
                    fStage[top] = 1;
                } else if (fStage[top] == 1) {
                    if (fI[top] >= bt->Order) {
                        res = fLeaf[top];
                        spT--;
                        if (spT > 0) fStage[spT-1] = 2;
                        continue;
                    }
                    long dsInner = np_dist(np, bt, fInner[top]);
                    if (dsInner < fDs[top]) {
                        fDsInner[top] = dsInner;
                        fIdx[spT] = fInner[top]; fAlt[spT] = fLeaf[top];
                        fDs[spT] = fDs[top]; fDepth[spT] = fDepth[top];
                        fStage[spT] = 0;
                        fStage[top] = 2;
                        spT++;
                    } else {
                        fStage[top] = 3;
                    }
                } else if (fStage[top] == 2) {
                    int leaf2 = res;
                    long dsLeaf2 = (fInner[top] == leaf2)
                            ? fDsInner[top] : np_dist(np, bt, leaf2);
                    if (dsLeaf2 < fDs[top]) {
                        fDs[top] = dsLeaf2;
                        fLeaf[top] = leaf2;
                    }
                    fStage[top] = 3;
                } else {
                    fInner[top] += fStep[top];
                    if (fInner[top] >= bt->Len) {
                        res = fLeaf[top];
                        spT--;
                        if (spT > 0) fStage[spT-1] = 2;
                    } else {
                        fI[top]++;
                        fStage[top] = 1;
                    }
                }
            }
            return res;
        }

        // ---------- 采样主函数 ----------
        int sample_biome(const PState* ps, const SplineBuf* sb, int root,
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
            np[0] = (long)(10000.0f * t);
            np[1] = (long)(10000.0f * h);
            np[2] = (long)(10000.0f * c);
            np[3] = (long)(10000.0f * e);
            np[4] = (long)(10000.0f * d);
            np[5] = (long)(10000.0f * w);
            return btree_biome(np, bt);
        }

        __kernel void scan_mushroom(
                int gw, int gh, int minX, int minZ, int step, int yq, int maxHits,
                __global const uchar*  S_D,
                __global const double* S_A, __global const double* S_B,
                __global const double* S_C, __global const double* S_D2,
                __global const double* S_T2, __global const double* S_AMP,
                __global const double* S_LAC, __global const int* S_H2,
                __global const int* C_OffA, __global const int* C_OffB,
                __global const int* C_NA, __global const int* C_NB,
                __global const double* C_AMP,
                __global const int* SP_Typ, __global const int* SP_Len,
                __global const float* SP_Val, __global const float* SP_Loc,
                __global const float* SP_Der, __global const int* SP_Child,
                int root,
                __global const int* BT_Steps, __global const int* BT_Param,
                __global const ulong* BT_Nodes, int BT_Order, int BT_Len,
                __global int* outCnt, __global ulong* outHits) {
            long gid = (long)get_global_id(0);
            if (gid >= (long)gw * gh) return;
            PState ps;
            ps.D = S_D; ps.A = S_A; ps.B = S_B; ps.C = S_C;
            ps.D2 = S_D2; ps.T2 = S_T2; ps.AMP = S_AMP; ps.LAC = S_LAC; ps.H2 = S_H2;
            SplineBuf sb;
            sb.Typ = SP_Typ; sb.Len = SP_Len; sb.Val = SP_Val;
            sb.Loc = SP_Loc; sb.Der = SP_Der; sb.Child = SP_Child;
            BTreeBuf bt;
            bt.Steps = BT_Steps; bt.Param = BT_Param; bt.Nodes = BT_Nodes;
            bt.Order = BT_Order; bt.Len = BT_Len;
            int i = (int)(gid % gw);
            int j = (int)(gid / gw);
            int x = minX + i * step + step / 2;
            int z = minZ + j * step + step / 2;
            long np[6];
            int id = sample_biome(&ps, &sb, root, &bt, np, x >> 2, yq, z >> 2);
            if (id == 14) {
                uint slot = atom_inc(outCnt);
                if ((long)slot < maxHits)
                    outHits[slot] = ((ulong)i << 32) | ((ulong)j & 0xFFFFFFFFUL);
            }
        }
    """;

    static final class GpuScanner {
        static boolean probeDone = false;
        static boolean available = false;
        static String unavailableReason = "";
        static org.jocl.cl_context ctx;
        static org.jocl.cl_command_queue queue;
        static org.jocl.cl_device_id dev;
        static org.jocl.cl_kernel kernel;
        static boolean stateAllocated = false;
        static org.jocl.cl_mem memD, memA, memB, memC, memD2, memT2, memH2,
                memPAMP, memPLAC, memCAMP, memOffA, memOffB, memNA, memNB,
                memSPTyp, memSPLen, memSPVal, memSPLoc, memSPDer, memSPChild,
                memBTSteps, memBTParam, memBTNodes, memOutCnt, memOutHits;

        static synchronized boolean available() {
            if (!probeDone) {
                probeDone = true;
                try {
                    initOpenCl();
                    available = true;
                } catch (Throwable ex) {
                    unavailableReason = String.valueOf(ex);
                    available = false;
                }
            }
            return available;
        }

        static void checkErr(int err, String what) throws Exception {
            if (err != org.jocl.CL.CL_SUCCESS)
                throw new Exception(what + " 失败: " + err);
        }

        static void initOpenCl() throws Exception {
            int[] n = new int[1];
            checkErr(org.jocl.CL.clGetPlatformIDs(0, null, n), "枚举 OpenCL 平台");
            if (n[0] == 0) throw new Exception("没有 OpenCL 平台");
            org.jocl.cl_platform_id[] ps = new org.jocl.cl_platform_id[n[0]];
            org.jocl.CL.clGetPlatformIDs(n[0], ps, null);
            org.jocl.cl_device_id gpu = null, any = null;
            org.jocl.cl_platform_id gpuPlat = null, anyPlat = null;
            for (org.jocl.cl_platform_id p : ps) {
                int[] dn = new int[1];
                if (org.jocl.CL.clGetDeviceIDs(p, org.jocl.CL.CL_DEVICE_TYPE_ALL,
                        0, null, dn) != org.jocl.CL.CL_SUCCESS) continue;
                org.jocl.cl_device_id[] ds = new org.jocl.cl_device_id[dn[0]];
                org.jocl.CL.clGetDeviceIDs(p, org.jocl.CL.CL_DEVICE_TYPE_ALL, dn[0], ds, null);
                for (org.jocl.cl_device_id d : ds) {
                    long[] type = new long[1];
                    org.jocl.CL.clGetDeviceInfo(d, org.jocl.CL.CL_DEVICE_TYPE, 8,
                            org.jocl.Pointer.to(type), null);
                    if ((type[0] & org.jocl.CL.CL_DEVICE_TYPE_GPU) != 0 && gpu == null) {
                        gpu = d; gpuPlat = p;
                    }
                    if (any == null) { any = d; anyPlat = p; }
                }
            }
            dev = gpu != null ? gpu : any;
            org.jocl.cl_platform_id plat = gpu != null ? gpuPlat : anyPlat;
            if (dev == null) throw new Exception("没有可用的 OpenCL 设备");
            org.jocl.cl_context_properties props = new org.jocl.cl_context_properties();
            props.addProperty(org.jocl.CL.CL_CONTEXT_PLATFORM, plat);
            ctx = org.jocl.CL.clCreateContext(props, 1, new org.jocl.cl_device_id[]{dev},
                    null, null, null, null);
            queue = org.jocl.CL.clCreateCommandQueueWithProperties(ctx, dev, null, null);
            org.jocl.cl_program prog = org.jocl.CL.clCreateProgramWithSource(ctx, 1,
                    new String[]{ GPU_KERNEL }, null, null);
            int err = org.jocl.CL.clBuildProgram(prog, 1, new org.jocl.cl_device_id[]{dev},
                    "-cl-fast-relaxed-math=off", null, null);
            if (err != org.jocl.CL.CL_SUCCESS) {
                long[] len = new long[1];
                org.jocl.CL.clGetProgramBuildInfo(prog, dev,
                        org.jocl.CL.CL_PROGRAM_BUILD_LOG, 0, null, len);
                byte[] log = new byte[(int) len[0]];
                org.jocl.CL.clGetProgramBuildInfo(prog, dev,
                        org.jocl.CL.CL_PROGRAM_BUILD_LOG, log.length,
                        org.jocl.Pointer.to(log), null);
                throw new Exception("内核编译失败: " + new String(log));
            }
            kernel = org.jocl.CL.clCreateKernel(prog, "scan_mushroom", null);
        }

        /** GPU 扫描: 返回 packed (i<<32|j) 命中数组 (与 CPU 流式扫描同格式)。 */
        static synchronized long[] scan(Cfg c, int gw, int gh) throws Exception {
            available();
            if (!available) throw new Exception("OpenCL 不可用: " + unavailableReason);

            // ---- 主机侧初始化种子状态 (与 Java setBiomeSeed 完全一致), 序列化 ----
            BiomeNoise bn = new BiomeNoise(c.ver);
            bn.setSeed(c.seed, c.large);
            int nP = 0;
            int[] offA = new int[6], offB = new int[6], nA = new int[6], nB = new int[6];
            double[] camp = new double[6];
            java.util.List<Perlin> perlins = new ArrayList<>();
            for (int ch = 0; ch < 6; ch++) {
                DoublePerlin dp = bn.climate[ch];
                offA[ch] = nP;
                for (int k = 0; k < dp.octA.n; k++) perlins.add(dp.octA.p[k]);
                nP += dp.octA.n; nA[ch] = dp.octA.n;
                offB[ch] = nP;
                for (int k = 0; k < dp.octB.n; k++) perlins.add(dp.octB.p[k]);
                nP += dp.octB.n; nB[ch] = dp.octB.n;
                camp[ch] = dp.amplitude;
            }
            byte[] sD = new byte[nP * 257];
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
            }

            // ---- 样条展平 ----
            java.util.List<Spline> spList = new ArrayList<>();
            flattenSpline(bn.root, spList);
            int nn = spList.size();
            int[] spTyp = new int[nn], spLen = new int[nn], spChild = new int[nn * 12];
            float[] spVal = new float[nn], spLoc = new float[nn * 12], spDer = new float[nn * 12];
            for (int i = 0; i < nn; i++) {
                Spline s = spList.get(i);
                spTyp[i] = s.typ; spLen[i] = s.len; spVal[i] = s.val;
                for (int k = 0; k < 12; k++) {
                    spLoc[i * 12 + k] = s.loc[k];
                    spDer[i * 12 + k] = s.der[k];
                    spChild[i * 12 + k] = s.len == 1 ? -1 :
                            java.util.Collections.indexOfSubList(spList,
                                    java.util.List.of(s.valArr[k]));
                }
            }

            BTree bt = BTREE[c.ver];

            // ---- 上传/分配 ----
            if (!stateAllocated) {
                allocBuffers(nP, nn, bt);
                stateAllocated = true;
            }
            upload(memD, sD); upload(memA, sA); upload(memB, sB); upload(memC, sC);
            upload(memD2, sD2); upload(memT2, sT2); upload(memH2, sH2);
            upload(memPAMP, sAMP); upload(memPLAC, sLAC); upload(memCAMP, camp);
            upload(memOffA, offA); upload(memOffB, offB); upload(memNA, nA); upload(memNB, nB);
            upload(memSPTyp, spTyp); upload(memSPLen, spLen); upload(memSPVal, spVal);
            upload(memSPLoc, spLoc); upload(memSPDer, spDer); upload(memSPChild, spChild);
            upload(memBTSteps, bt.steps); upload(memBTParam, bt.param); upload(memBTNodes, bt.nodes);

            int maxHits = (int) Math.min(2_000_000L, (long) gw * gh);
            if (maxHits > curMaxHits) {
                if (memOutCnt != null) org.jocl.CL.clReleaseMemObject(memOutCnt);
                if (memOutHits != null) org.jocl.CL.clReleaseMemObject(memOutHits);
                memOutCnt = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 4, null, null);
                memOutHits = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_WRITE_ONLY,
                        (long) maxHits * 8, null, null);
                curMaxHits = maxHits;
            }
            org.jocl.CL.clEnqueueFillBuffer(queue, memOutCnt, org.jocl.Pointer.to(new int[]{0}),
                    org.jocl.Sizeof.cl_int, 0, 4, 0, null, null);

            // ---- 参数 ----
            int a = 0;
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{gw}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{gh}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{c.minX}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{c.minZ}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{c.step}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{c.yq}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{maxHits}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memD}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memA}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memB}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memC}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memD2}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memT2}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memPAMP}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memPLAC}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memH2}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOffA}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOffB}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memNA}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memNB}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memCAMP}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPTyp}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPLen}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPVal}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPLoc}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPDer}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPChild}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{0}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTSteps}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTParam}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTNodes}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.order}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.len}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOutCnt}));
            org.jocl.CL.clSetKernelArg(kernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOutHits}));

            long global = ((long) gw * gh + 255L) / 256L * 256L;
            int err = org.jocl.CL.clEnqueueNDRangeKernel(queue, kernel, 1, null,
                    new long[]{ global }, new long[]{ 256 }, 0, null, null);
            checkErr(err, "GPU 启动");
            org.jocl.CL.clFinish(queue);

            int[] cnt = new int[1];
            org.jocl.CL.clEnqueueReadBuffer(queue, memOutCnt, org.jocl.CL.CL_TRUE, 0, 4,
                    org.jocl.Pointer.to(cnt), 0, null, null);
            int got = Math.min(cnt[0], maxHits);
            long[] hits = new long[got];
            if (got > 0)
                org.jocl.CL.clEnqueueReadBuffer(queue, memOutHits, org.jocl.CL.CL_TRUE, 0,
                        (long) got * 8, org.jocl.Pointer.to(hits), 0, null, null);
            return hits;
        }

        static void upload(org.jocl.cl_mem mem, Object arr) {
            long size;
            org.jocl.Pointer ptr;
            if (arr instanceof byte[] a) { size = a.length; ptr = org.jocl.Pointer.to(a); }
            else if (arr instanceof int[] a) { size = (long) a.length * 4; ptr = org.jocl.Pointer.to(a); }
            else if (arr instanceof double[] a) { size = (long) a.length * 8; ptr = org.jocl.Pointer.to(a); }
            else if (arr instanceof long[] a) { size = (long) a.length * 8; ptr = org.jocl.Pointer.to(a); }
            else if (arr instanceof float[] a) { size = (long) a.length * 4; ptr = org.jocl.Pointer.to(a); }
            else throw new IllegalArgumentException();
            org.jocl.CL.clEnqueueWriteBuffer(queue, mem, org.jocl.CL.CL_TRUE, 0, size, ptr, 0, null, null);
        }

        static void allocBuffers(int nP, int nn, BTree bt) throws Exception {
            memD = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 257, null, null);
            memA = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memB = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memD2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memT2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memH2 = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 4, null, null);
            memPAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memPLAC = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nP * 8, null, null);
            memCAMP = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 8L, null, null);
            memOffA = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 4L, null, null);
            memOffB = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 4L, null, null);
            memNA = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 4L, null, null);
            memNB = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 6 * 4L, null, null);
            memSPTyp = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 4, null, null);
            memSPLen = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 4, null, null);
            memSPVal = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 4, null, null);
            memSPLoc = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 12 * 4, null, null);
            memSPDer = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 12 * 4, null, null);
            memSPChild = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, (long) nn * 12 * 4, null, null);
            memBTSteps = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY,
                    (long) bt.steps.length * 4, null, null);
            memBTParam = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY,
                    (long) bt.param.length * 4, null, null);
            memBTNodes = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY,
                    (long) bt.nodes.length * 8, null, null);
        }

        static void flattenSpline(Spline s, java.util.List<Spline> out) {
            if (java.util.Collections.indexOfSubList(out, java.util.List.of(s)) >= 0) return;
            out.add(s);
            if (s.len > 1)
                for (int k = 0; k < s.len; k++)
                    flattenSpline(s.valArr[k], out);
        }
    }
