#!/usr/bin/env python3
"""v2.4 补丁A: 周长(外露边数) + 紧凑度指标, 粗筛与细化两级都计算。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. Island 增加字段
old = """    static final class Island {
        int cx, cz, w, h;
        long area;
        double dist;
    }"""
new = """    static final class Island {
        int cx, cz, w, h;
        long area;
        long perimeter;      // 周长(方块): 组件内格子的外露边数 × 步长
        double compactness;  // 紧凑度 = 4π·面积/周长², 1.0 为正圆, 越小越破碎
        double dist;
    }"""
assert old in src, "Island"
src = src.replace(old, new)

# 2. coarseIslands: 统计每个连通分量的外露边数
old = """        for (int k = 0; k < n; k++) {
            if (hsFind(parent, k) != k) continue;
            Island isl = new Island();
            isl.cx = c.minX + (int) (sumI[k] / cntA[k]) * c.step + c.step / 2;
            isl.cz = c.minZ + (int) (sumJ[k] / cntA[k]) * c.step + c.step / 2;
            isl.w = (maxI[k] - minI[k] + 1) * c.step;
            isl.h = (maxJ[k] - minJ[k] + 1) * c.step;
            isl.area = (long) cntA[k] * c.step * c.step;
            isl.dist = Math.hypot(isl.cx, isl.cz);
            out.add(isl);
        }
        return out;
    }"""
new = """        // 外露边数: 命中格的 4 邻域中非命中格的数量 (按根分量累计)
        long[] peri = new long[n];
        for (int k = 0; k < n; k++) {
            int i = (int) (hits[k] >>> 32), j = (int) hits[k];
            int root = hsFind(parent, k);
            if (!cellIdx.containsKey(packCell(i - 1, j))) peri[root]++;
            if (!cellIdx.containsKey(packCell(i + 1, j))) peri[root]++;
            if (!cellIdx.containsKey(packCell(i, j - 1))) peri[root]++;
            if (!cellIdx.containsKey(packCell(i, j + 1))) peri[root]++;
        }
        for (int k = 0; k < n; k++) {
            if (hsFind(parent, k) != k) continue;
            Island isl = new Island();
            isl.cx = c.minX + (int) (sumI[k] / cntA[k]) * c.step + c.step / 2;
            isl.cz = c.minZ + (int) (sumJ[k] / cntA[k]) * c.step + c.step / 2;
            isl.w = (maxI[k] - minI[k] + 1) * c.step;
            isl.h = (maxJ[k] - minJ[k] + 1) * c.step;
            isl.area = (long) cntA[k] * c.step * c.step;
            isl.perimeter = peri[k] * c.step;
            isl.compactness = peri[k] > 0
                    ? 4 * Math.PI * cntA[k] / ((double) peri[k] * peri[k]) : 1.0;
            isl.dist = Math.hypot(isl.cx, isl.cz);
            out.add(isl);
        }
        return out;
    }

    static long packCell(int i, int j) {
        return ((long) i << 32) | (j & 0xFFFFFFFFL);
    }"""
assert old in src, "coarseIslands"
src = src.replace(old, new)

# 3. refine(): 细化网格上同步统计外露边数
old = """            while (sp > 0) {
                int cur = stack[--sp];
                int ci2 = cur % fw, cj2 = cur / fw;
                cnt++; sumI += ci2; sumJ += cj2;
                if (ci2 < i0) i0 = ci2;
                if (ci2 > i1) i1 = ci2;
                if (cj2 < j0) j0 = cj2;
                if (cj2 > j1) j1 = cj2;
                if (ci2 > 0      && m2[cur - 1]   == 1 && !vis[cur - 1])  { vis[cur - 1] = true;  stack[sp++] = cur - 1; }
                if (ci2 < fw - 1 && m2[cur + 1]   == 1 && !vis[cur + 1])  { vis[cur + 1] = true;  stack[sp++] = cur + 1; }
                if (cj2 > 0      && m2[cur - fw]  == 1 && !vis[cur - fw]) { vis[cur - fw] = true; stack[sp++] = cur - fw; }
                if (cj2 < fh - 1 && m2[cur + fw]  == 1 && !vis[cur + fw]) { vis[cur + fw] = true; stack[sp++] = cur + fw; }
            }
            if (cnt > bestCnt) {
                bestCnt = cnt; bestSumI = sumI; bestSumJ = sumJ;
                bi0 = i0; bi1 = i1; bj0 = j0; bj1 = j1;
            }"""
new = """            long edges = 0;
            while (sp > 0) {
                int cur = stack[--sp];
                int ci2 = cur % fw, cj2 = cur / fw;
                cnt++; sumI += ci2; sumJ += cj2;
                if (ci2 < i0) i0 = ci2;
                if (ci2 > i1) i1 = ci2;
                if (cj2 < j0) j0 = cj2;
                if (cj2 > j1) j1 = cj2;
                // 外露边: 4 邻域越界或非命中 (含区域边界, 区域已留足余量)
                if (ci2 == 0      || m2[cur - 1]  == 0) edges++;
                if (ci2 == fw - 1 || m2[cur + 1]  == 0) edges++;
                if (cj2 == 0      || m2[cur - fw] == 0) edges++;
                if (cj2 == fh - 1 || m2[cur + fw] == 0) edges++;
                if (ci2 > 0      && m2[cur - 1]   == 1 && !vis[cur - 1])  { vis[cur - 1] = true;  stack[sp++] = cur - 1; }
                if (ci2 < fw - 1 && m2[cur + 1]   == 1 && !vis[cur + 1])  { vis[cur + 1] = true;  stack[sp++] = cur + 1; }
                if (cj2 > 0      && m2[cur - fw]  == 1 && !vis[cur - fw]) { vis[cur - fw] = true; stack[sp++] = cur - fw; }
                if (cj2 < fh - 1 && m2[cur + fw]  == 1 && !vis[cur + fw]) { vis[cur + fw] = true; stack[sp++] = cur + fw; }
            }
            if (cnt > bestCnt) {
                bestCnt = cnt; bestSumI = sumI; bestSumJ = sumJ;
                bestEdges = edges;
                bi0 = i0; bi1 = i1; bj0 = j0; bj1 = j1;
            }"""
assert old in src, "refine fill"
src = src.replace(old, new)

old = """        long bestCnt = 0, bestSumI = 0, bestSumJ = 0;
        int bi0 = 0, bi1 = 0, bj0 = 0, bj1 = 0;"""
new = """        long bestCnt = 0, bestSumI = 0, bestSumJ = 0, bestEdges = 0;
        int bi0 = 0, bi1 = 0, bj0 = 0, bj1 = 0;"""
assert old in src, "refine vars"
src = src.replace(old, new)

old = """        if (bestCnt > 0) {
            isl.cx = bx0 + (int) (bestSumI / bestCnt) * fs + fs / 2;
            isl.cz = bz0 + (int) (bestSumJ / bestCnt) * fs + fs / 2;
            isl.w = (bi1 - bi0 + 1) * fs;
            isl.h = (bj1 - bj0 + 1) * fs;
            isl.area = bestCnt * (long) fs * fs;
            isl.dist = Math.hypot(isl.cx, isl.cz);
        }"""
new = """        if (bestCnt > 0) {
            isl.cx = bx0 + (int) (bestSumI / bestCnt) * fs + fs / 2;
            isl.cz = bz0 + (int) (bestSumJ / bestCnt) * fs + fs / 2;
            isl.w = (bi1 - bi0 + 1) * fs;
            isl.h = (bj1 - bj0 + 1) * fs;
            isl.area = bestCnt * (long) fs * fs;
            isl.perimeter = bestEdges * fs;
            isl.compactness = bestEdges > 0
                    ? 4 * Math.PI * bestCnt / ((double) bestEdges * bestEdges) : 1.0;
            isl.dist = Math.hypot(isl.cx, isl.cz);
        }"""
assert old in src, "refine apply"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patch A ok")
