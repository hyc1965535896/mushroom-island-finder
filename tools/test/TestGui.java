import javax.swing.*;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** GUI 回归测试：模拟两个标签页的真实操作，验证 v1.1 的"请输入种子"误报已修复。 */
public class TestGui {
    public static void main(String[] args) throws Exception {
        FindMushroomIslands.GuiFrame frame = new FindMushroomIslands.GuiFrame();

        // ---- 标签页1: 单种子搜索（用户截图中的场景: 种子 20260721）----
        FindMushroomIslands.FormRefs f = frame.fSeed;
        SwingUtilities.invokeAndWait(() -> {
            f.seedField.setText("20260721");
            f.threadsField.setText("4");
            f.startBtn.doClick();
        });
        long t0 = System.currentTimeMillis();
        while (System.currentTimeMillis() - t0 < 60000) {
            final boolean[] done = new boolean[1];
            SwingUtilities.invokeAndWait(() -> done[0] = f.startBtn.isEnabled());
            if (done[0]) break;
            Thread.sleep(200);
        }
        final StringBuilder r1 = new StringBuilder();
        SwingUtilities.invokeAndWait(() -> r1.append(f.output.getText()));
        boolean pass1 = r1.toString().contains("找到") || r1.toString().contains("未找到");
        System.out.println("TAB1(single seed): " + (pass1 ? "OK" : "FAIL"));
        System.out.println("  first line: " + r1.toString().split("\n")[0]);

        // ---- 标签页2: 种子列表批量搜索（不填种子框，应不再误报）----
        Files.write(Path.of("test_seeds.txt"), List.of("# 注释行", "20260721", "12345"));
        FindMushroomIslands.FormRefs fl = frame.fList;
        SwingUtilities.invokeAndWait(() -> {
            fl.listFileField.setText("test_seeds.txt");
            fl.threadsField.setText("4");
            fl.startBtn.doClick();
        });
        t0 = System.currentTimeMillis();
        while (System.currentTimeMillis() - t0 < 120000) {
            final boolean[] done = new boolean[1];
            SwingUtilities.invokeAndWait(() -> done[0] = fl.startBtn.isEnabled());
            if (done[0]) break;
            Thread.sleep(200);
        }
        final StringBuilder r2 = new StringBuilder();
        SwingUtilities.invokeAndWait(() -> r2.append(fl.output.getText()));
        boolean pass2 = r2.length() > 0 && r2.toString().contains("种子:");
        System.out.println("TAB2(seed list): " + (pass2 ? "OK" : "FAIL"));
        System.out.println("  contains seed lines: " + r2.toString().contains("20260721"));

        Files.deleteIfExists(Path.of("test_seeds.txt"));
        System.out.println(pass1 && pass2 ? "GUI_REGRESSION_PASS" : "GUI_REGRESSION_FAIL");
        System.exit(pass1 && pass2 ? 0 : 1);
    }
}
