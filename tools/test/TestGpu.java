import java.util.*;

/** GPU vs CPU 命中一致性验证: 两套实现必须在同一网格上给出完全相同的命中集合。 */
public class TestGpu {
    public static void main(String[] args) throws Exception {
        if (!FindMushroomIslands.GpuScanner.available()) {
            System.out.println("OpenCL 不可用: " + FindMushroomIslands.GpuScanner.unavailableReason);
            System.exit(2);
        }
        long t0 = System.nanoTime();
        boolean allOk = true;

        // 场景1: 原点附近 ±16384, 步长64 (低坐标)
        allOk &= compare(20260721, -16384, 16384, 64, false);
        // 场景2: 用户实测的大坐标岛附近 (422800, -1029200) ±8192, 步长128
        allOk &= compare(20260721, 422800 - 8192, 422800 + 8192, 128, false,
                -1029200 - 8192, -1029200 + 8192);
        // 场景3: 步长512 大范围小样 (±1M, 抽查一致性)
        allOk &= compare(20260721, -1000000, 1000000, 512, false);

        double secs = (System.nanoTime() - t0) / 1e9;
        System.out.println(allOk ? "GPU_VS_CPU_PASS (" + secs + "s)" : "GPU_VS_CPU_FAIL");
        System.exit(allOk ? 0 : 1);
    }

    static boolean compare(long seed, int minX, int maxX, int step, boolean large) {
        return compare(seed, minX, maxX, step, large, minX, maxX);
    }

    static boolean compare(long seed, int minX, int maxX, int step, boolean large,
            int minZ, int maxZ) {
        FindMushroomIslands.Cfg c = new FindMushroomIslands.Cfg();
        c.seed = seed; c.seedText = String.valueOf(seed);
        c.minX = minX; c.maxX = maxX; c.minZ = minZ; c.maxZ = maxZ;
        c.step = step; c.large = large;
        int gw = (c.maxX - c.minX) / c.step;
        int gh = (c.maxZ - c.minZ) / c.step;

        // CPU 命中
        FindMushroomIslands.BiomeNoise bn = new FindMushroomIslands.BiomeNoise(c.ver);
        bn.setSeed(c.seed, c.large);
        TreeSet<Long> cpu = new TreeSet<>();
        for (int j = 0; j < gh; j++) {
            int z = c.minZ + j * c.step + c.step / 2;
            for (int i = 0; i < gw; i++) {
                int x = c.minX + i * c.step + c.step / 2;
                if (FindMushroomIslands.sampleBiomeNoise(bn, null, x >> 2, c.yq, z >> 2)
                        == FindMushroomIslands.B_MUSHROOM)
                    cpu.add(((long) i << 32) | (j & 0xFFFFFFFFL));
            }
        }

        // GPU 命中
        try {
            FindMushroomIslands.GpuScanner.scan(c, gw, gh);
            long[] g = FindMushroomIslands.GpuScanner.scan(c, gw, gh); // 第二次跑走已分配路径
            TreeSet<Long> gpu = new TreeSet<>();
            for (long v : g) gpu.add(v);

            boolean ok = cpu.equals(gpu);
            System.out.printf("区域 [%d,%d]x[%d,%d] 步长%d: CPU命中=%d GPU命中=%d %s%n",
                    minX, maxX, minZ, maxZ, step, cpu.size(), gpu.size(),
                    ok ? "一致 OK" : "不一致 FAIL");
            if (!ok) {
                Set<Long> onlyC = new TreeSet<>(cpu); onlyC.removeAll(gpu);
                Set<Long> onlyG = new TreeSet<>(gpu); onlyG.removeAll(cpu);
                System.out.println("  仅CPU: " + first(onlyC, 5) + "  仅GPU: " + first(onlyG, 5));
            }
            return ok;
        } catch (Exception ex) {
            System.out.println("GPU 扫描异常: " + ex);
            return false;
        }
    }

    static String first(Set<Long> s, int n) {
        StringBuilder sb = new StringBuilder();
        for (long v : s) {
            if (n-- == 0) break;
            sb.append("(").append(v >>> 32).append(",").append(v & 0xFFFFFFFFL).append(") ");
        }
        return sb.toString();
    }
}
