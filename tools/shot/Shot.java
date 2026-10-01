import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;

/** 一次性工具：启动 GUI，用 Swing 自渲染截取窗口内容到 docs/screenshot.png（不被遮挡）。 */
public class Shot {
    public static void main(String[] args) throws Exception {
        FindMushroomIslands.main(new String[0]);
        Thread.sleep(5000); // 等窗口初始化
        for (Window w : Window.getWindows()) {
            if (w instanceof JFrame && w.isVisible()) {
                Dimension d = w.getSize();
                BufferedImage img = new BufferedImage(d.width, d.height,
                        BufferedImage.TYPE_INT_RGB);
                w.printAll(img.getGraphics());
                File out = new File("docs/screenshot.png");
                out.getParentFile().mkdirs();
                ImageIO.write(img, "png", out);
                System.out.println("saved " + out.getAbsolutePath() + " " + d.width + "x" + d.height);
            }
        }
        System.exit(0);
    }
}
