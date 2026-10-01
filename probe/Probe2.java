import org.jocl.*;
import static org.jocl.CL.*;
public class Probe2 {
    public static void main(String[] a) {
        int[] n = new int[1];
        clGetPlatformIDs(0, null, n);
        cl_platform_id[] ps = new cl_platform_id[n[0]];
        clGetPlatformIDs(n[0], ps, null);
        for (cl_platform_id p : ps) {
            int[] dn = new int[1];
            if (clGetDeviceIDs(p, CL_DEVICE_TYPE_ALL, 0, null, dn) != CL_SUCCESS) continue;
            cl_device_id[] ds = new cl_device_id[dn[0]];
            clGetDeviceIDs(p, CL_DEVICE_TYPE_ALL, dn[0], ds, null);
            for (cl_device_id d : ds) {
                long[] len = new long[1];
                clGetDeviceInfo(d, CL_DEVICE_EXTENSIONS, 0, null, len);
                byte[] b = new byte[(int) len[0]];
                clGetDeviceInfo(d, CL_DEVICE_EXTENSIONS, b.length, Pointer.to(b), null);
                String ext = new String(b);
                System.out.println("fp64KHR=" + ext.contains("cl_khr_fp64"));
                System.out.println("int64Base=" + ext.contains("cl_khr_int64_base_atomics"));
                int[] v = new int[1];
                clGetDeviceInfo(d, CL_DEVICE_NATIVE_VECTOR_WIDTH_DOUBLE, 4, Pointer.to(v), null);
                System.out.println("nativeDoubleWidth=" + v[0]);
            }
        }
    }
}
