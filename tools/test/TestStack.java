import java.util.*;

/** 在 Java 里逐字复刻内核的栈式 btree, 与递归版对比, 定位分歧。 */
public class TestStack {
    static FindMushroomIslands.BTree bt = FindMushroomIslands.BTREE[0];

    static long npDist(long[] np, int idx) {
        long node = bt.nodes[idx];
        long ds = 0;
        for (int i = 0; i < 6; i++) {
            int pi = (int) ((node >>> (8 * i)) & 0xFF);
            long a = np[i] - bt.param[2 * pi + 1];
            long b = bt.param[2 * pi] - np[i];
            long d = a > 0 ? a : (b > 0 ? b : 0);
            ds += d * d;
        }
        return ds;
    }

    // 内核栈式状态机的 Java 镜像
    static int stackSearch(long[] np) {
        int[] fIdx = new int[10]; int[] fAlt = new int[10]; int[] fDepth = new int[10];
        int[] fStep = new int[10]; int[] fInner = new int[10]; int[] fLeaf = new int[10];
        int[] fI = new int[10]; int[] fStage = new int[10];
        long[] fDs = new long[10]; long[] fDsInner = new long[10];
        int spT = 1;
        int res = 0;
        fIdx[0] = 0; fAlt[0] = 0; fDs[0] = 0x7FFFFFFFFFFFFFFFL; fDepth[0] = 0; fStage[0] = 0;
        while (spT > 0) {
            int top = spT - 1;
            if (fStage[top] == 0) {
                if (bt.steps[fDepth[top]] == 0) {
                    res = fIdx[top];
                    spT--;
                    if (spT > 0) fStage[spT - 1] = 2;
                    continue;
                }
                int step;
                do {
                    step = bt.steps[fDepth[top]];
                    fDepth[top]++;
                } while (fIdx[top] + step >= bt.len);
                fStep[top] = step;
                fInner[top] = (int) ((bt.nodes[fIdx[top]] >>> 48) & 0xFFFF);
                fLeaf[top] = fAlt[top];
                fI[top] = 0;
                fStage[top] = 1;
            } else if (fStage[top] == 1) {
                if (fI[top] >= bt.order) {
                    res = fLeaf[top];
                    spT--;
                    if (spT > 0) fStage[spT - 1] = 2;
                    continue;
                }
                long dsInner = npDist(np, fInner[top]);
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
                long dsLeaf2 = (fInner[top] == leaf2) ? fDsInner[top] : npDist(np, leaf2);
                if (dsLeaf2 < fDs[top]) {
                    fDs[top] = dsLeaf2;
                    fLeaf[top] = leaf2;
                }
                fStage[top] = 3;
            } else {
                fInner[top] += fStep[top];
                if (fInner[top] >= bt.len) {
                    res = fLeaf[top];
                    spT--;
                    if (spT > 0) fStage[spT - 1] = 2;
                } else {
                    fI[top]++;
                    fStage[top] = 1;
                }
            }
        }
        return res;
    }

    // 递归参考版
    static int recSearch(long[] np, int idx, int alt, long ds, int depth) {
        if (bt.steps[depth] == 0) return idx;
        int step;
        do {
            step = bt.steps[depth];
            depth++;
        } while (idx + step >= bt.len);
        long node = bt.nodes[idx];
        int inner = (int) ((node >>> 48) & 0xFFFF);
        int leaf = alt;
        for (int i = 0; i < bt.order; i++) {
            long dsInner = npDist(np, inner);
            if (dsInner < ds) {
                int leaf2 = recSearch(np, inner, leaf, ds, depth);
                long dsLeaf2 = inner == leaf2 ? dsInner : npDist(np, leaf2);
                if (dsLeaf2 < ds) {
                    ds = dsLeaf2;
                    leaf = leaf2;
                }
            }
            inner += step;
            if (inner >= bt.len) break;
        }
        return leaf;
    }

    public static void main(String[] args) {
        long[] np = {-3510, -1072, -10728, -2215, -311, -3809};
        int stack = stackSearch(np);
        int rec = recSearch(np, 0, 0, Long.MAX_VALUE, 0);
        System.out.println("栈式=" + stack + "  递归=" + rec
                + "  栈式群系=" + ((bt.nodes[stack] >>> 48) & 0xFF)
                + "  递归群系=" + ((bt.nodes[rec] >>> 48) & 0xFF));
        System.out.println("nodes[0]>>48(inner)=" + ((bt.nodes[0] >>> 48) & 0xFFFF)
                + "  order=" + bt.order + "  len=" + bt.len
                + "  steps=" + Arrays.toString(bt.steps));
    }
}
