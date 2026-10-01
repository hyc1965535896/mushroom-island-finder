#!/usr/bin/env python3
"""加 debug_btree 内核: 直接输入 np, 输出最终节点 idx 与群系。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

old = """            long np[6];
            int id = sample_biome(&ps, &sb, root, &bt, np, gx >> 2, yq, gz >> 2);
            for (int k = 0; k < 6; k++) outNp[k] = np[k];
            outId[0] = id;
        }
    \"\"\";"""
new = """            long np[6];
            int id = sample_biome(&ps, &sb, root, &bt, np, gx >> 2, yq, gz >> 2);
            for (int k = 0; k < 6; k++) outNp[k] = np[k];
            outId[0] = id;
        }

        __kernel void debug_btree(
                __global const long* inNp,
                __global const int* BT_Steps, __global const int* BT_Param,
                __global const ulong* BT_Nodes, int BT_Order, int BT_Len,
                __global long* outRes) {
            BTreeBuf bt;
            bt.Steps = BT_Steps; bt.Param = BT_Param; bt.Nodes = BT_Nodes;
            bt.Order = BT_Order; bt.Len = BT_Len;
            long np[6];
            for (int k = 0; k < 6; k++) np[k] = inNp[k];
            int idx = btree_search(np, &bt);
            outRes[0] = idx;
            outRes[1] = btree_biome(np, &bt);
        }

        int btree_search(const long* np, const BTreeBuf* bt) {
            int   fIdx[10]; int fAlt[10]; int fDepth[10]; int fStep[10];
            int   fInner[10]; int fLeaf[10]; int fI[10]; int fStage[10];
            long  fDs[10]; long fDsInner[10];
            int spT = 1;
            int res = 0;
            fIdx[0] = 0; fAlt[0] = 0; fDs[0] = 0x7FFFFFFFFFFFFFFFL; fDepth[0] = 0; fStage[0] = 0;
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
                    long dsLeaf2 = (fInner[top] == leaf2) ? fDsInner[top] : np_dist(np, bt, leaf2);
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
    \"\"\";"""
assert old in src, "kernel tail"
src = src.replace(old, new)

# debugSample 之外加 debugBtree 方法
old = """        static org.jocl.cl_mem memOutNp, memOutId;"""
new = """        static org.jocl.cl_mem memOutNp, memOutId, memBtIn, memBtOut;
        static org.jocl.cl_kernel debugBtreeKernel;
        static boolean btreeKernelReady = false;

        /** 调试: 直接用 np 跑内核 btree, 返回 {Long idx, Long biome}。 */
        static synchronized Object[] debugBtree(long[] np, int ver) throws Exception {
            available();
            if (!available) throw new Exception("OpenCL 不可用");
            if (!btreeKernelReady) {
                debugBtreeKernel = org.jocl.CL.clCreateKernel(progRef, "debug_btree", null);
                memBtIn = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_ONLY, 48, null, null);
                memBtOut = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 16, null, null);
                btreeKernelReady = true;
            }
            BTree bt = BTREE[ver];
            org.jocl.CL.clEnqueueWriteBuffer(queue, memBtIn, org.jocl.CL.CL_TRUE, 0, 48,
                    org.jocl.Pointer.to(np), 0, null, null);
            int a = 0;
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBtIn}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTSteps}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTParam}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBTNodes}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.order}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_int, org.jocl.Pointer.to(new int[]{bt.len}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBtOut}));
            org.jocl.CL.clEnqueueNDRangeKernel(queue, debugBtreeKernel, 1, null, new long[]{1}, new long[]{1}, 0, null, null);
            org.jocl.CL.clFinish(queue);
            long[] out = new long[2];
            org.jocl.CL.clEnqueueReadBuffer(queue, memBtOut, org.jocl.CL.CL_TRUE, 0, 16,
                    org.jocl.Pointer.to(out), 0, null, null);
            return new Object[]{ out[0], out[1] };
        }"""
assert old in src, "debugSample anchor"
src = src.replace(old, new)

# 保存 program 引用
src = src.replace("""        static org.jocl.cl_device_id dev;
        static org.jocl.cl_kernel kernel;""",
"""        static org.jocl.cl_device_id dev;
        static org.jocl.cl_program progRef;
        static org.jocl.cl_kernel kernel;""")
src = src.replace("""            kernel = org.jocl.CL.clCreateKernel(prog, "scan_mushroom", null);
            debugKernel = org.jocl.CL.clCreateKernel(prog, "debug_cell", null);""",
"""            progRef = prog;
            kernel = org.jocl.CL.clCreateKernel(prog, "scan_mushroom", null);
            debugKernel = org.jocl.CL.clCreateKernel(prog, "debug_cell", null);""")

p.write_text(src, encoding="utf-8")
print("patched ok")
