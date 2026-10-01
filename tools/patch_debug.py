#!/usr/bin/env python3
"""给内核加 debug_cell 调试入口 + 主机 debugSample 方法。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. 内核源码尾部加 debug_cell
old = """            if (id == 14) {
                uint slot = atom_inc(outCnt);
                if ((long)slot < maxHits)
                    outHits[slot] = ((ulong)i << 32) | ((ulong)j & 0xFFFFFFFFUL);
            }
        }
    \"\"\";"""
new = """            if (id == 14) {
                uint slot = atom_inc(outCnt);
                if ((long)slot < maxHits)
                    outHits[slot] = ((ulong)i << 32) | ((ulong)j & 0xFFFFFFFFUL);
            }
        }

        __kernel void debug_cell(
                int gx, int gz, int yq,
                __global const uchar*  S_D,
                __global const float* S_A, __global const float* S_B,
                __global const float* S_C, __global const float* S_D2,
                __global const float* S_T2, __global const float* S_AMP,
                __global const float* S_LAC, __global const int* S_H2,
                __global const int* C_OffA, __global const int* C_OffB,
                __global const int* C_NA, __global const int* C_NB,
                __global const float* C_AMP,
                __global const int* SP_Typ, __global const int* SP_Len,
                __global const float* SP_Val, __global const float* SP_Loc,
                __global const float* SP_Der, __global const int* SP_Child,
                int root,
                __global const int* BT_Steps, __global const int* BT_Param,
                __global const ulong* BT_Nodes, int BT_Order, int BT_Len,
                __global long* outNp, __global int* outId) {
            PState ps;
            ps.D = S_D; ps.A = S_A; ps.B = S_B; ps.C = S_C;
            ps.D2 = S_D2; ps.T2 = S_T2; ps.AMP = S_AMP; ps.LAC = S_LAC; ps.H2 = S_H2;
            ps.OffA = C_OffA; ps.OffB = C_OffB; ps.NA = C_NA; ps.NB = C_NB; ps.CAMP = C_AMP;
            SplineBuf sb;
            sb.Typ = SP_Typ; sb.Len = SP_Len; sb.Val = SP_Val;
            sb.Loc = SP_Loc; sb.Der = SP_Der; sb.Child = SP_Child;
            BTreeBuf bt;
            bt.Steps = BT_Steps; bt.Param = BT_Param; bt.Nodes = BT_Nodes;
            bt.Order = BT_Order; bt.Len = BT_Len;
            long np[6];
            int id = sample_biome(&ps, &sb, root, &bt, np, gx >> 2, yq, gz >> 2);
            for (int k = 0; k < 6; k++) outNp[k] = np[k];
            outId[0] = id;
        }
    \"\"\";"""
assert old in src, "kernel tail"
src = src.replace(old, new)

# 2. debug kernel 字段
old = "        static org.jocl.cl_kernel kernel;"
new = """        static org.jocl.cl_kernel kernel;
        static org.jocl.cl_kernel debugKernel;"""
assert old in src, "kernel field"
src = src.replace(old, new)

old = '            kernel = org.jocl.CL.clCreateKernel(prog, "scan_mushroom", null);'
new = """            kernel = org.jocl.CL.clCreateKernel(prog, "scan_mushroom", null);
            debugKernel = org.jocl.CL.clCreateKernel(prog, "debug_cell", null);"""
assert old in src, "kernel create"
src = src.replace(old, new)

# 3. debugSample 方法 (追加在 scan 方法结束后)
old = """            int got = Math.min(cnt[0], maxHits);
            long[] hits = new long[got];
            if (got > 0)
                org.jocl.CL.clEnqueueReadBuffer(queue, memOutHits, org.jocl.CL.CL_TRUE, 0,
                        (long) got * 8, org.jocl.Pointer.to(hits), 0, null, null);
            return hits;
        }"""
new = """            int got = Math.min(cnt[0], maxHits);
            long[] hits = new long[got];
            if (got > 0)
                org.jocl.CL.clEnqueueReadBuffer(queue, memOutHits, org.jocl.CL.CL_TRUE, 0,
                        (long) got * 8, org.jocl.Pointer.to(hits), 0, null, null);
            return hits;
        }

        static org.jocl.cl_mem memOutNp, memOutId;

        /** 调试: 在上次 scan 的种子状态下采样单个世界坐标, 返回 {long[6] np, Integer id}。 */
        static synchronized Object[] debugSample(int x, int z, int yq, int ver) throws Exception {
            available();
            if (!available) throw new Exception("OpenCL 不可用");
            BTree bt = BTREE[ver];
            long[] outNp = new long[6];
            int[] outId = new int[1];
            int a = 0;
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{x}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{z}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{yq}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memD}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memA}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memB}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memC}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memD2}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memT2}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memPAMP}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memPLAC}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memH2}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOffA}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOffB}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memNA}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memNB}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memCAMP}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPTyp}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPLen}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPVal}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPLoc}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPDer}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memSPChild}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{0}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTSteps}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTParam}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTNodes}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.order}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.len}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOutNp}));
            org.jocl.CL.clSetKernelArg(debugKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memOutId}));
            org.jocl.CL.clEnqueueNDRangeKernel(queue, debugKernel, 1, null,
                    new long[]{1}, new long[]{1}, 0, null, null);
            org.jocl.CL.clFinish(queue);
            org.jocl.CL.clEnqueueReadBuffer(queue, memOutNp, org.jocl.CL.CL_TRUE, 0, 48,
                    org.jocl.Pointer.to(outNp), 0, null, null);
            org.jocl.CL.clEnqueueReadBuffer(queue, memOutId, org.jocl.CL.CL_TRUE, 0, 4,
                    org.jocl.Pointer.to(outId), 0, null, null);
            return new Object[]{ outNp, outId[0] };
        }"""
assert old in src, "debugSample"
src = src.replace(old, new)

# 4. allocBuffers 分配调试缓冲
old = """            memBTNodes = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY,
                    (long) bt.nodes.length * 8, null, null);
        }"""
new = """            memBTNodes = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY,
                    (long) bt.nodes.length * 8, null, null);
            memOutNp = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 48, null, null);
            memOutId = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 4, null, null);
        }"""
assert old in src, "alloc"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patched ok")
