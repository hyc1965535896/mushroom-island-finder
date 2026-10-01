#!/usr/bin/env python3
"""btree_search 加追踪输出定位首次分歧。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. btree_search 加 trace 参数与记录
old = """        int btree_search(const long* np, const BTreeBuf* bt) {"""
new = """        int btree_search(const long* np, const BTreeBuf* bt, __global long* trace) {"""
assert old in src, "sig"
src = src.replace(old, new)

old = """            int spT = 1;
            int res = 0;
            fIdx[0] = 0; fAlt[0] = 0; fDs[0] = 0x7FFFFFFFFFFFFFFFL; fDepth[0] = 0; fStage[0] = 0;
            while (spT > 0) {
                int top = spT - 1;
                if (fStage[top] == 0) {
                    if (bt->Steps[fDepth[top]] == 0) {"""
new = """            int spT = 1;
            int res = 0;
            int tN = 0;
            fIdx[0] = 0; fAlt[0] = 0; fDs[0] = 0x7FFFFFFFFFFFFFFFL; fDepth[0] = 0; fStage[0] = 0;
            while (spT > 0) {
                int top = spT - 1;
                if (fStage[top] == 0) {
                    if (tN < 60) trace[tN++] = ((long)fDepth[top] << 32) | (long)fIdx[top];
                    if (bt->Steps[fDepth[top]] == 0) {"""
assert old in src, "trace entry"
src = src.replace(old, new)

old = """                    } else {
                        fI[top]++;
                        fStage[top] = 1;
                    }
                }
            }
            return res;
        }
    \"\"\";"""
new = """                    } else {
                        fI[top]++;
                        fStage[top] = 1;
                    }
                }
            }
            if (tN < 60) trace[tN++] = -1L;
            return res;
        }
    \"\"\";"""
assert old in src, "trace end"
src = src.replace(old, new)

# 2. debug_btree 调用处传入 trace
old = """        __kernel void debug_btree(
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
        }"""
new = """        __kernel void debug_btree(
                __global const long* inNp,
                __global const int* BT_Steps, __global const int* BT_Param,
                __global const ulong* BT_Nodes, int BT_Order, int BT_Len,
                __global long* outRes, __global long* trace) {
            BTreeBuf bt;
            bt.Steps = BT_Steps; bt.Param = BT_Param; bt.Nodes = BT_Nodes;
            bt.Order = BT_Order; bt.Len = BT_Len;
            long np[6];
            for (int k = 0; k < 6; k++) np[k] = inNp[k];
            int idx = btree_search(np, &bt, trace);
            outRes[0] = idx;
            outRes[1] = (long)(((bt->Nodes[idx] >> 48)) & 0xFF);
        }"""
assert old in src, "debug_btree body"
src = src.replace(old, new)

# 3. 主机: trace 缓冲 + 参数
old = """                memBtOut = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 16, null, null);
                btreeKernelReady = true;"""
new = """                memBtOut = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 16, null, null);
                memBtTrace = org.jocl.CL.clCreateBuffer(ctx, org.jocl.CL.CL_MEM_READ_WRITE, 64 * 8L, null, null);
                btreeKernelReady = true;"""
assert old in src, "trace buf"
src = src.replace(old, new)

old = """        static org.jocl.cl_mem memOutNp, memOutId, memBtIn, memBtOut;"""
new = """        static org.jocl.cl_mem memBtIn, memBtOut, memBtTrace;"""
assert old in src, "trace field"
src = src.replace(old, new)

old = """            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBtOut}));
            org.jocl.CL.clEnqueueNDRangeKernel(queue, debugBtreeKernel, 1, null, new long[]{1}, new long[]{1}, 0, null, null);
            org.jocl.CL.clFinish(queue);
            long[] out = new long[2];
            org.jocl.CL.clEnqueueReadBuffer(queue, memBtOut, org.jocl.CL.CL_TRUE, 0, 16,
                    org.jocl.Pointer.to(out), 0, null, null);
            return new Object[]{ out[0], out[1] };"""
new = """            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBtOut}));
            org.jocl.CL.clSetKernelArg(debugBtreeKernel, a++, org.jocl.Sizeof.cl_mem, org.jocl.Pointer.to(new org.jocl.cl_mem[]{memBtTrace}));
            org.jocl.CL.clEnqueueNDRangeKernel(queue, debugBtreeKernel, 1, null, new long[]{1}, new long[]{1}, 0, null, null);
            org.jocl.CL.clFinish(queue);
            long[] out = new long[2];
            org.jocl.CL.clEnqueueReadBuffer(queue, memBtOut, org.jocl.CL.CL_TRUE, 0, 16,
                    org.jocl.Pointer.to(out), 0, null, null);
            long[] tr = new long[64];
            org.jocl.CL.clEnqueueReadBuffer(queue, memBtTrace, org.jocl.CL.CL_TRUE, 0, 64 * 8L,
                    org.jocl.Pointer.to(tr), 0, null, null);
            return new Object[]{ out[0], out[1], tr };"""
assert old in src, "trace read"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patched ok")
