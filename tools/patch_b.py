#!/usr/bin/env python3
"""v2.4 补丁B/C: 输出行加周长紧凑度、buildReport 重构、CSV/JSON 导出、复制坐标、-o、阶段前缀。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# ---------- 1. CLI 输出行加周长/紧凑度 ----------
old = """            System.out.printf(
                "#%-3d 中心 (%d, %d)  范围 %d x %d  面积 ≈ %,d 方块^2  距原点 %,d%n",
                rank++, isl.cx, isl.cz, isl.w, isl.h, isl.area, (long) isl.dist);"""
new = """            System.out.printf(
                "#%-3d 中心 (%d, %d)  范围 %d x %d  面积 ≈ %,d  周长 %,d  紧凑度 %.2f  距原点 %,d%n",
                rank++, isl.cx, isl.cz, isl.w, isl.h, isl.area,
                isl.perimeter, isl.compactness, (long) isl.dist);"""
assert old in src, "cli line"
src = src.replace(old, new)

# ---------- 2. CLI -o 输出文件 ----------
old = """            case "-center":"""
assert old in src, "center case b"
src = src.replace(old, """            case "-o":    outFile = args[++i]; break;
            case "-center":""", 1)
old = """        Cfg c = new Cfg();
        boolean stepSet = false;
        int centerX = 0, centerZ = 0;
        boolean hasCenter = false;
        c.seedText = args[0];"""
new = """        Cfg c = new Cfg();
        boolean stepSet = false;
        int centerX = 0, centerZ = 0;
        boolean hasCenter = false;
        String outFile = null;
        c.seedText = args[0];"""
assert old in src, "outFile decl"
src = src.replace(old, new)

old = """        System.out.printf("找到 %d 个蘑菇岛 (耗时 %.1f 秒):%n", list.size(), secs);
        int rank = 1;"""
new = """        System.out.printf("找到 %d 个蘑菇岛 (耗时 %.1f 秒):%n", list.size(), secs);
        if (outFile != null) {
            String s = outFile.toLowerCase(java.util.Locale.ROOT).endsWith(".csv") ? buildCsv(c, list)
                    : outFile.toLowerCase(java.util.Locale.ROOT).endsWith(".json") ? buildJson(c, list)
                    : buildReport(c, list, false);
            java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), s);
            System.out.println("结果已写入 " + outFile);
        }
        int rank = 1;"""
assert old in src, "cli write"
src = src.replace(old, new)

# ---------- 3. buildReport / buildCsv / buildJson 静态方法 (放在 finishScan 后) ----------
old = """    /** 聚类 + 细化 + 面积筛选 (CPU/GPU 共用)。 */
    static List<Island> finishScan(Cfg c, Progress prog, long[] hits) {"""
new = """    /** 文本报告 (GUI 与 CLI 共用)。append=true 时用于多种子累积。 */
    static String buildReport(Cfg c, List<Island> list, boolean append) {
        StringBuilder sb = new StringBuilder();
        if (append)
            sb.append("\\n──────────────────────\\n");
        sb.append(t("种子: ", "Seed: ")).append(c.seedText);
        if (!c.seedText.matches("[+-]?[0-9]+"))
            sb.append(t("  (数值: ", "  (numeric: ")).append(c.seed).append(")");
        sb.append('\\n');
        sb.append(t("版本: ", "Version: ")).append(VER_NAMES[c.ver])
          .append(c.large ? t("  大型生物群系", "  Large Biomes") : "")
          .append('\\n');
        sb.append(String.format(
                t("区域: [%d, %d] x [%d, %d]  分辨率: %d方块/格%n",
                  "Region: [%d, %d] x [%d, %d]  resolution: %d blocks/cell%n"),
                c.minX, c.maxX, c.minZ, c.maxZ, c.step));
        if (c.step >= 1024)
            sb.append(t("警告: 步长较大, 直径明显小于步长的蘑菇岛可能漏检; 可在\\"分辨率\\"中选择更细步长。\\n",
                        "Warning: coarse step, islands much smaller than the step may be missed; pick a finer resolution.\\n"));
        if (list.isEmpty()) {
            sb.append(t("未找到蘑菇岛, 可尝试扩大搜索区域。\\n",
                        "No mushroom island found, try a larger region.\\n"));
        } else {
            sb.append(String.format(
                    t("找到 %d 个蘑菇岛 (按面积降序):%n",
                      "Found %d mushroom island(s):%n"), list.size()));
            int rank = 1;
            for (Island isl : list) {
                sb.append(String.format(
                        "#%-3d %s (%d, %d)  %s %d x %d  %s ≈ %,d %s  %s %,d  %s %.2f  %s %,d%n",
                        rank++,
                        t("中心", "center"), isl.cx, isl.cz,
                        t("范围", "size"), isl.w, isl.h,
                        t("面积", "area"), isl.area, t("方块²", "blocks²"),
                        t("周长", "perim"), isl.perimeter,
                        t("紧凑度", "compact"), isl.compactness,
                        t("距原点", "dist"), (long) isl.dist));
            }
            sb.append(t(
                "提示: 面积为近似值; 游戏内可用 /locate biome minecraft:mushroom_fields 验证。\\n",
                "Tip: areas are approximate; verify with /locate biome minecraft:mushroom_fields.\\n"));
        }
        return sb.toString();
    }

    static String buildCsv(Cfg c, List<Island> list) {
        StringBuilder sb = new StringBuilder("﻿"); // BOM: Excel 直开不乱码
        sb.append("rank,seed,version,x,z,width,height,area,perimeter,compactness,distance
");
        String seed = c.seedText.replace('"', ''');
        String ver = (VER_NAMES[c.ver] + (c.large ? " (LB)" : "")).replace('"', ''');
        int rank = 1;
        for (Island i : list) {
            sb.append(rank++).append(",\"").append(seed).append("\",\"").append(ver).append("\",")
              .append(i.cx).append(',').append(i.cz).append(',')
              .append(i.w).append(',').append(i.h).append(',')
              .append(i.area).append(',').append(i.perimeter).append(',')
              .append(String.format(java.util.Locale.ROOT, "%.3f", i.compactness))
              .append(',').append((long) i.dist).append('
');
        }
        return sb.toString();
    }

    static String jsonStr(String s) {
        return "\"" + s.replace('"', ''') + "\"";
    }

    static String buildJson(Cfg c, List<Island> list) {
        StringBuilder sb = new StringBuilder("{
");
        sb.append("  \"seed\": ").append(jsonStr(c.seedText)).append(",
");
        sb.append("  \"seedNumeric\": ").append(c.seed).append(",
");
        sb.append("  \"version\": ").append(jsonStr(VER_NAMES[c.ver] + (c.large ? " (LB)" : ""))).append(",
");
        sb.append("  \"region\": {\"minX\": ").append(c.minX)
          .append(", \"maxX\": ").append(c.maxX)
          .append(", \"minZ\": ").append(c.minZ)
          .append(", \"maxZ\": ").append(c.maxZ)
          .append(", \"step\": ").append(c.step).append("},
");
        sb.append("  \"islands\": [
");
        int rank = 1;
        for (Island i : list) {
            sb.append("    {\"rank\": ").append(rank)
              .append(", \"x\": ").append(i.cx)
              .append(", \"z\": ").append(i.cz)
              .append(", \"width\": ").append(i.w)
              .append(", \"height\": ").append(i.h)
              .append(", \"area\": ").append(i.area)
              .append(", \"perimeter\": ").append(i.perimeter)
              .append(", \"compactness\": ").append(String.format(java.util.Locale.ROOT, "%.4f", i.compactness))
              .append(", \"distance\": ").append((long) i.dist).append('}');
            sb.append(rank < list.size() ? "," : "");
            sb.append('
');
            rank++;
        }
        sb.append("  ]
}
");
        return sb.toString();
    }

    /** 聚类 + 细化 + 面积筛选 (CPU/GPU 共用)。 */
    static List<Island> finishScan(Cfg c, Progress prog, long[] hits) {"""
new = """    /** 文本报告 (GUI 与 CLI 共用)。append=true 时用于多种子累积。 */
    static String buildReport(Cfg c, List<Island> list, boolean append) {
        StringBuilder sb = new StringBuilder();
        if (append)
            sb.append("\\n──────────────────────\\n");
        sb.append(t("种子: ", "Seed: ")).append(c.seedText);
        if (!c.seedText.matches("[+-]?[0-9]+"))
            sb.append(t("  (数值: ", "  (numeric: ")).append(c.seed).append(")");
        sb.append('\\n');
        sb.append(t("版本: ", "Version: ")).append(VER_NAMES[c.ver])
          .append(c.large ? t("  大型生物群系", "  Large Biomes") : "")
          .append('\\n');
        sb.append(String.format(
                t("区域: [%d, %d] x [%d, %d]  分辨率: %d方块/格%n",
                  "Region: [%d, %d] x [%d, %d]  resolution: %d blocks/cell%n"),
                c.minX, c.maxX, c.minZ, c.maxZ, c.step));
        if (c.step >= 1024)
            sb.append(t("警告: 步长较大, 直径明显小于步长的蘑菇岛可能漏检; 可在\\"分辨率\\"中选择更细步长。\\n",
                        "Warning: coarse step, islands much smaller than the step may be missed; pick a finer resolution.\\n"));
        if (list.isEmpty()) {
            sb.append(t("未找到蘑菇岛, 可尝试扩大搜索区域。\\n",
                        "No mushroom island found, try a larger region.\\n"));
        } else {
            sb.append(String.format(
                    t("找到 %d 个蘑菇岛 (按面积降序):%n",
                      "Found %d mushroom island(s):%n"), list.size()));
            int rank = 1;
            for (Island isl : list) {
                sb.append(String.format(
                        "#%-3d %s (%d, %d)  %s %d x %d  %s ≈ %,d %s  %s %,d  %s %.2f  %s %,d%n",
                        rank++,
                        t("中心", "center"), isl.cx, isl.cz,
                        t("范围", "size"), isl.w, isl.h,
                        t("面积", "area"), isl.area, t("方块²", "blocks²"),
                        t("周长", "perim"), isl.perimeter,
                        t("紧凑度", "compact"), isl.compactness,
                        t("距原点", "dist"), (long) isl.dist));
            }
            sb.append(t(
                "提示: 面积为近似值; 游戏内可用 /locate biome minecraft:mushroom_fields 验证。\\n",
                "Tip: areas are approximate; verify with /locate biome minecraft:mushroom_fields.\\n"));
        }
        return sb.toString();
    }

    static String buildCsv(Cfg c, List<Island> list) {
        StringBuilder sb = new StringBuilder("\\uFEFF"); // BOM: Excel 直开不乱码
        sb.append("rank,seed,version,x,z,width,height,area,perimeter,compactness,distance\\n");
        String seed = c.seedText.replace("\\"", "\\"\\"");
        String ver = VER_NAMES[c.ver] + (c.large ? " (LB)" : "");
        int rank = 1;
        for (Island i : list) {
            sb.append(rank++).append(",\\"").append(seed).append("\\",\\"").append(ver).append("\\",")
              .append(i.cx).append(',').append(i.cz).append(',')
              .append(i.w).append(',').append(i.h).append(',')
              .append(i.area).append(',').append(i.perimeter).append(',')
              .append(String.format(java.util.Locale.ROOT, "%.3f", i.compactness))
              .append(',').append((long) i.dist).append('\\n');
        }
        return sb.toString();
    }

    static String jsonStr(String s) {
        return "\\"" + s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"") + "\\"";
    }

    static String buildJson(Cfg c, List<Island> list) {
        StringBuilder sb = new StringBuilder("{\\n");
        sb.append("  \\"seed\\": ").append(jsonStr(c.seedText)).append(",\\n");
        sb.append("  \\"seedNumeric\\": ").append(c.seed).append(",\\n");
        sb.append("  \\"version\\": ").append(jsonStr(VER_NAMES[c.ver] + (c.large ? " (LB)" : ""))).append(",\\n");
        sb.append("  \\"region\\": {\\"minX\\": ").append(c.minX)
          .append(", \\"maxX\\": ").append(c.maxX)
          .append(", \\"minZ\\": ").append(c.minZ)
          .append(", \\"maxZ\\": ").append(c.maxZ)
          .append(", \\"step\\": ").append(c.step).append("},\\n");
        sb.append("  \\"islands\\": [\\n");
        int rank = 1;
        for (Island i : list) {
            sb.append("    {\\"rank\\": ").append(rank)
              .append(", \\"x\\": ").append(i.cx)
              .append(", \\"z\\": ").append(i.cz)
              .append(", \\"width\\": ").append(i.w)
              .append(", \\"height\\": ").append(i.h)
              .append(", \\"area\\": ").append(i.area)
              .append(", \\"perimeter\\": ").append(i.perimeter)
              .append(", \\"compactness\\": ").append(String.format(java.util.Locale.ROOT, "%.4f", i.compactness))
              .append(", \\"distance\\": ").append((long) i.dist).append('}');
            sb.append(rank < list.size() ? "," : "");
            sb.append('\\n');
            rank++;
        }
        sb.append("  ]\\n}\\n");
        return sb.toString();
    }

    /** 聚类 + 细化 + 面积筛选 (CPU/GPU 共用)。 */
    static List<Island> finishScan(Cfg c, Progress prog, long[] hits) {"""
assert old in src, "builders anchor"
src = src.replace(old, new)

# finishScan 开头加聚类阶段
old = """    static List<Island> finishScan(Cfg c, Progress prog, long[] hits) {
        List<Island> out = coarseIslands(hits, c);"""
new = """    static List<Island> finishScan(Cfg c, Progress prog, long[] hits) {
        prog.phase(t("聚类中...", "Clustering..."));
        List<Island> out = coarseIslands(hits, c);"""
assert old in src, "cluster phase"
src = src.replace(old, new)

p.write_text(src, encoding="utf-8")
print("patch B1 ok")
