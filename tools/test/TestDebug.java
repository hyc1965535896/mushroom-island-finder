import java.util.*;

/** 对比 CPU 与 GPU 在同一命中药点的六维气候值。 */
public class TestDebug {
    public static void main(String[] args) throws Exception {
        long seed = 20260721;
        // 用户实测大坐标岛附近的 CPU 命中药点 (来自 TestGpu 场景2): 格 (18,72), 步长128
        int minX = 422800 - 8192, minZ = -1029200 - 8192, step = 128;
        int i = 18, j = 72;
        int x = minX + i * step + step / 2;
        int z = minZ + j * step + step / 2;

        // CPU
        FindMushroomIslands.BiomeNoise bn = new FindMushroomIslands.BiomeNoise(0);
        bn.setSeed(seed, false);
        long[] cpuNp = new long[6];
        int cpuId = FindMushroomIslands.sampleBiomeNoise(bn, cpuNp, x >> 2, 16, z >> 2);

        // GPU (状态需先由 scan 初始化)
        FindMushroomIslands.Cfg c = new FindMushroomIslands.Cfg();
        c.seed = seed; c.seedText = String.valueOf(seed);
        c.minX = minX; c.maxX = 422800 + 8192; c.minZ = minZ; c.maxZ = -1029200 + 8192;
        c.step = step;
        FindMushroomIslands.GpuScanner.scan(c, (c.maxX - c.minX) / c.step,
                (c.maxZ - c.minZ) / c.step);
        Object[] dbg = FindMushroomIslands.GpuScanner.debugSample(x, z, 16, 0);
        long[] gpuNp = (long[]) dbg[0];
        int gpuId = (Integer) dbg[1];

        String[] names = {"温度", "湿度", "大陆性", "侵蚀", "深度", "奇异性"};
        System.out.println("采样点 block (" + x + ", " + z + ") quart(" + (x >> 2) + "," + (z >> 2) + ")");
        System.out.printf("%-8s %10s %10s %8s%n", "通道", "CPU", "GPU", "差");
        for (int k = 0; k < 6; k++)
            System.out.printf("%-8s %10d %10d %8d%n", names[k], cpuNp[k], gpuNp[k], gpuNp[k] - cpuNp[k]);
        System.out.println("群系ID: CPU=" + cpuId + " GPU=" + gpuId);
    }
}
