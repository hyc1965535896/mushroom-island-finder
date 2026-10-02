import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;

/** 截取"从种子列表搜索"标签页, 验证文件选择行可见。 */
public class Shot2 {
    public static void main(String[] args) throws Exception {
        FindMushroomIslands.main(new String[0]);
        Thread.sleep(5000);
        for (Window w : Window.getWindows()) {
            if (w instanceof JFrame jf && jf.isVisible()) {
                for (Component c : jf.getContentPane().getComponents()) {
                    if (c instanceof JTabbedPane tp) {
                        tp.setSelectedIndex(1);
                        break;
                    }
                }
                Thread.sleep(800);
                Dimension d = jf.getSize();
                BufferedImage img = new BufferedImage(d.width, d.height,
                        BufferedImage.TYPE_INT_RGB);
                jf.printAll(img.getGraphics());
                ImageIO.write(img, "png", new File("docs/screenshot_list.png"));
                System.out.println("saved docs/screenshot_list.png");
            }
        }
        System.exit(0);
    }
}
