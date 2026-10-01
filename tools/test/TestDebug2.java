import java.util.*;

/** 决定性实验: 扫描内核 vs 调试内核 在同一单元格上是否一致。 */
public class TestDebug2 {
    public static void main(String[] args) throws Exception {
        FindMushroomIslands.Cfg c = new FindMushroomIslands.Cfg();
        c.seed = 20260721; c.seedText = "20260721";
        c.minX = -16384; c.maxX = 16384; c.minZ = -16384; c.maxZ = 16384;
        c.step = 64;
        int gw = (c.maxX - c.minX) / c.step, gh = (c.maxZ - c.minZ) / c.step;

        long[] hits = FindMushroomIslands.GpuScanner.scan(c, gw, gh);
        Set<Long> gpu = new HashSet<>();
        for (long v : hits) gpu.add(v);

        // CPU 命中格 (5,291) 与 GPU 独有格 (5,408)
        int[][] cells = {{5, 291}, {5, 408}};
        for (int[] cell : cells) {
            int i = cell[0], j = cell[1];
            int x = c.minX + i * c.step + c.step / 2;
            int z = c.minZ + j * c.step + c.step / 2;
            Object[] dbg = FindMushroomIslands.GpuScanner.debugSample(x, z, 16, 4);
            long[] np = (long[]) dbg[0];
            int id = (Integer) dbg[1];
            boolean inScan = gpu.contains(((long) i << 32) | (j & 0xFFFFFFFFL));
            int javaCheck = FindMushroomIslands.climateToBiome(4, np);
            long javaIdx = FindMushroomIslands.getResultingNode(np,
                    FindMushroomIslands.BTREE[4], 0, 0, Long.MAX_VALUE, 0);
            Object[] bt = FindMushroomIslands.GpuScanner.debugBtree(np, 4);
            long[] out = (long[]) bt[3];
            System.out.printf("cell(%d,%d): debugId=%d JavaBtree=%d 内核Btree=%d(节点%d) Java节点=%d%n",
                    i, j, id, javaCheck, out[1], out[0], javaIdx);
            System.out.println("  Steps回显=" + Arrays.toString(Arrays.copyOfRange(out, 4, 10))
                    + " Len=" + out[10] + " Order=" + out[11] + " nodes[0]inner=" + out[12]);
            long[] tr = (long[]) bt[2];
            StringBuilder tsb = new StringBuilder("  内核追踪: ");
            for (long v : tr) {
                if (v == -1) break;
                tsb.append("(d").append(v >>> 32).append(",n").append(v & 0xFFFFFFFFL).append(") ");
            }
            System.out.println(tsb);
        }

        // CPU 参照
        FindMushroomIslands.BiomeNoise bn = new FindMushroomIslands.BiomeNoise(4);
        bn.setSeed(c.seed, false);
        for (int[] cell : cells) {
            int i = cell[0], j = cell[1];
            int x = c.minX + i * c.step + c.step / 2;
            int z = c.minZ + j * c.step + c.step / 2;
            long[] np = new long[6];
            int id = FindMushroomIslands.sampleBiomeNoise(bn, np, x >> 2, 16, z >> 2);
            System.out.printf("CPU cell(%d,%d): id=%d np=%s%n", i, j, id, Arrays.toString(np));
        }
    }
}
