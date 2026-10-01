import org.jocl.*;
import static org.jocl.CL.*;
public class Probe {
    public static void main(String[] a) {
        int[] n = new int[1];
        clGetPlatformIDs(0, null, n);
        System.out.println("platforms=" + n[0]);
        cl_platform_id[] ps = new cl_platform_id[n[0]];
        clGetPlatformIDs(n[0], ps, null);
        for (cl_platform_id p : ps) {
            System.out.println("P: " + infoStr(p, CL_PLATFORM_NAME) + " / " + infoStr(p, CL_PLATFORM_VERSION));
            int[] dn = new int[1];
            if (clGetDeviceIDs(p, CL_DEVICE_TYPE_ALL, 0, null, dn) != CL_SUCCESS) continue;
            cl_device_id[] ds = new cl_device_id[dn[0]];
            clGetDeviceIDs(p, CL_DEVICE_TYPE_ALL, dn[0], ds, null);
            for (cl_device_id d : ds) {
                long[] type = new long[1];
                clGetDeviceInfo(d, CL_DEVICE_TYPE, 8, Pointer.to(type), null);
                String t = (type[0] & CL_DEVICE_TYPE_GPU) != 0 ? "GPU" : "CPU/ACC";
                System.out.println("  D[" + t + "]: " + infoStr(d, CL_DEVICE_NAME) + "  [" + infoStr(d, CL_DEVICE_VERSION) + "]");
            }
        }
    }
    static String infoStr(cl_platform_id p, int k) {
        long[] len = new long[1];
        clGetPlatformInfo(p, k, 0, null, len);
        byte[] b = new byte[(int) len[0]];
        clGetPlatformInfo(p, k, b.length, Pointer.to(b), null);
        return new String(b).trim();
    }
    static String infoStr(cl_device_id d, int k) {
        long[] len = new long[1];
        clGetDeviceInfo(d, k, 0, null, len);
        byte[] b = new byte[(int) len[0]];
        clGetDeviceInfo(d, k, b.length, Pointer.to(b), null);
        return new String(b).trim();
    }
}
