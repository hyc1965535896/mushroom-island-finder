import javax.swing.*;
import java.awt.*;

/** 复现用户场景: 种子 20260721, ±3M, 分辨率 512, 观察预览文本是否滚动更新。 */
public class TestPreview {
    public static void main(String[] args) throws Exception {
        FindMushroomIslands.GuiFrame frame = new FindMushroomIslands.GuiFrame();
        FindMushroomIslands.FormRefs f = frame.fSeed;
        SwingUtilities.invokeAndWait(() -> {
            f.seedField.setText("20260721");
            f.threadsField.setText("8");
            f.resBox.setSelectedIndex(4); // 512
            f.sideField.setText("6000000");
            f.startBtn.doClick();
        });
        for (int t = 0; t < 8; t++) {
            Thread.sleep(2500);
            final String[] txt = new String[1];
            SwingUtilities.invokeAndWait(() -> txt[0] = f.output.getText());
            String head = txt[0].split("\n").length > 0 ? txt[0].split("\n")[0] : "";
            System.out.println("t=" + (t + 1) * 2500 + "ms  lines=" +
                    txt[0].split("\n").length + "  | " + head);
            if (t == 2 || t == 5)
                System.out.println("---- snapshot ----\n" + txt[0].substring(0,
                        Math.min(400, txt[0].length())) + "\n----");
        }
        System.exit(0);
    }
}
