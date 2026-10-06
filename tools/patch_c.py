#!/usr/bin/env python3
"""v2.4 补丁C(重写干净版): GUI 复制坐标/导出格式对话框/lastCfg/报告重构/阶段前缀/版本号。"""
import pathlib

p = pathlib.Path("FindMushroomIslands.java")
src = p.read_text(encoding="utf-8")

# 1. FormRefs 加 copyBtn
old = "        JButton startBtn, pauseBtn, stopBtn, resetBtn, exportBtn, sortBtn, browseBtn, selfTestBtn;"
new = "        JButton startBtn, pauseBtn, stopBtn, resetBtn, exportBtn, sortBtn, browseBtn, selfTestBtn, copyBtn;"
assert old in src, "FormRefs btns"
src = src.replace(old, new)

# 2. rbtns 加复制坐标按钮
old = """            f.exportBtn.addActionListener(e -> exportResults(f));
            f.sortBtn.addActionListener(e -> {
                lastSortByDist = !lastSortByDist;
                renderLast(f);
            });
            rbtns.add(f.exportBtn); rbtns.add(f.sortBtn);"""
new = """            f.exportBtn.addActionListener(e -> exportResults(f));
            f.copyBtn = new JButton(t("复制坐标", "Copy"));
            f.copyBtn.addActionListener(e -> copyCoords());
            f.sortBtn.addActionListener(e -> {
                lastSortByDist = !lastSortByDist;
                renderLast(f);
            });
            rbtns.add(f.exportBtn); rbtns.add(f.copyBtn); rbtns.add(f.sortBtn);"""
assert old in src, "rbtns"
src = src.replace(old, new)

# 3. renderSeedResult(append) 委托给 buildReport (终点 = renderLast 头)
start = src.index("        void renderSeedResult(FormRefs f, Cfg c, List<Island> list, boolean append) {")
end = src.index("        void renderLast(FormRefs f) {")
src = src[:start] + """        void renderSeedResult(FormRefs f, Cfg c, List<Island> list, boolean append) {
            String s = buildReport(c, list, append);
            if (append) {
                f.output.append(s);
            } else {
                f.output.setText(s);
                f.output.setCaretPosition(0);
            }
        }

""" + src[end:]

# 4. lastCfg 字段
old = """        List<Island> lastIslands = new ArrayList<>();
        String lastSeedText = "";
        boolean lastSortByDist = false;"""
new = """        List<Island> lastIslands = new ArrayList<>();
        Cfg lastCfg;
        String lastSeedText = "";
        boolean lastSortByDist = false;"""
assert old in src, "lastCfg field"
src = src.replace(old, new)

old = """                    lastIslands = list;
                    lastSeedText = c.seedText;"""
new = """                    lastIslands = list;
                    lastCfg = cloneCfg(c);
                    lastSeedText = c.seedText;"""
assert old in src, "lastCfg set"
src = src.replace(old, new)

# 5. renderLast 用 lastCfg
old = """            Cfg tmp = new Cfg();
            tmp.seedText = lastSeedText;
            tmp.ver = 0;
            renderSeedResult(f, tmp, copy);"""
new = """            Cfg tmp = lastCfg != null ? lastCfg : new Cfg();
            tmp.seedText = lastSeedText;
            renderSeedResult(f, tmp, copy);"""
assert old in src, "renderLast"
src = src.replace(old, new)

# 6. exportResults: 格式对话框 + 结构化导出 (终点 = 入口节注释, 补类结束括号)
start = src.index("        void exportResults(FormRefs f) {")
end = src.index("    //==========================================================================", start)
src = src[:start] + """        void exportResults(FormRefs f) {
            if (lastCfg == null || lastIslands.isEmpty()) {
                JOptionPane.showMessageDialog(this,
                        t("还没有可导出的结果", "Nothing to export yet"),
                        t("导出", "Export"), JOptionPane.INFORMATION_MESSAGE);
                return;
            }
            int fmt = JOptionPane.showOptionDialog(this,
                    t("选择导出格式:", "Choose export format:"),
                    t("导出", "Export"), JOptionPane.DEFAULT_OPTION,
                    JOptionPane.QUESTION_MESSAGE, null,
                    new Object[]{"TXT", "CSV", "JSON"}, "CSV");
            if (fmt < 0) return;
            String[] ext = {"txt", "csv", "json"};
            JFileChooser fc = new JFileChooser();
            fc.setSelectedFile(new File("mushroom_islands." + ext[fmt]));
            if (fc.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
            File file = fc.getSelectedFile();
            String s = fmt == 1 ? buildCsv(lastCfg, lastIslands)
                     : fmt == 2 ? buildJson(lastCfg, lastIslands)
                     : buildReport(lastCfg, lastIslands, false);
            try (Writer w = new OutputStreamWriter(
                    new FileOutputStream(file), StandardCharsets.UTF_8)) {
                w.write(s);
            } catch (IOException ex) {
                JOptionPane.showMessageDialog(this, ex.toString(),
                        t("导出失败", "Export failed"), JOptionPane.ERROR_MESSAGE);
            }
        }

        void copyCoords() {
            if (lastIslands.isEmpty()) return;
            StringBuilder sb = new StringBuilder();
            for (Island isl : lastIslands)
                sb.append(isl.cx).append(' ').append(isl.cz).append('\\n');
            java.awt.datatransfer.StringSelection sel =
                    new java.awt.datatransfer.StringSelection(sb.toString());
            java.awt.Toolkit.getDefaultToolkit().getSystemClipboard()
                    .setContents(sel, sel);
        }
    }


""" + src[end:]

# 7. ScanUi 采样阶段前缀
old = """                    f.bar.setValue((int) Math.round(frac * 10000));
                    f.progressLabel.setText(String.format(
                            t("进度: %d/%d (%.2f%%)", "Progress: %d/%d (%.2f%%)"),
                            s, total, frac * 100));"""
new = """                    f.bar.setValue((int) Math.round(frac * 10000));
                    f.progressLabel.setText(t("[采样] ", "[Sampling] ") + String.format(
                            t("进度: %d/%d (%.2f%%)", "Progress: %d/%d (%.2f%%)"),
                            s, total, frac * 100));"""
assert old in src, "scan prefix"
src = src.replace(old, new)

# 8. 版本号
src = src.replace('    static final String VERSION = "2.3";',
                  '    static final String VERSION = "2.4";', 1)

p.write_text(src, encoding="utf-8")
print("patch C ok (clean rewrite)")
