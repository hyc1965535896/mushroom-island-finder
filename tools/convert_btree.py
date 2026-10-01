#!/usr/bin/env python3
"""Convert cubiomes tables/btreeXX.h into Java fields and splice them into
FindMushroomIslands.java.

The node tables are ~9k uint64 each; Java static initializers share one
<clinit> with a 64KB bytecode limit, so the tables are embedded as chunked
string constants (constant-pool limit 65535B per literal) and decoded at
class-init time by decodeInts()/decodeHex() (expected to exist in the class).
"""
import re, sys, pathlib

REF = pathlib.Path(__file__).resolve().parent.parent / "_ref" / "cubiomes-master" / "tables"
OUT = pathlib.Path(__file__).resolve().parent.parent / "FindMushroomIslands.java"
START = "    static final int BT18_ORDER"
END = "    static final int V18 = 0, V192 = 1, V19 = 2, V20 = 3, V21WD = 4;"

def parse_header(path: pathlib.Path, tag: str):
    txt = path.read_text()
    order = int(re.search(rf"enum \{{ btree{tag}_order = (\d+) \}};", txt).group(1))
    steps = re.search(rf"static const uint32_t btree{tag}_steps\[\] = \{{([^;]*)\}};", txt).group(1)
    steps = [int(x) for x in steps.replace("\n", " ").split(",") if x.strip()]
    pm = re.search(rf"static const int32_t btree{tag}_param\[\]\[2\] =\s*\{{(.*?)\n\}};", txt, re.S)
    # strip // comments first: line comments like "// 00-03" contain digits!
    pm_clean = re.sub(r"//[^\n]*", "", pm.group(1))
    nums = [int(x) for x in re.findall(r"-?\d+", pm_clean)]
    assert len(nums) % 2 == 0
    nm = re.search(rf"static const uint64_t btree{tag}_nodes\[\] =\s*\{{(.*?)\n\}};", txt, re.S)
    nodes = re.findall(r"0x([0-9a-fA-F]{16})", nm.group(1))
    return order, steps, nums, nodes

def chunk_strings(chars, per_chunk=3000):
    """Split a char sequence into Java string literals of <= per_chunk items."""
    lits = []
    for i in range(0, len(chars), per_chunk):
        lits.append('"' + "".join(chars[i:i+per_chunk]) + '"')
    return lits

def emit(tag: str) -> str:
    order, steps, params, nodes = parse_header(REF / f"btree{tag}.h", tag)
    u = tag.upper()
    L = []
    L.append(f"    static final int BT{u}_ORDER = {order};")
    L.append(f"    static final int[] BT{u}_STEPS = {{ {', '.join(map(str, steps))} }};")
    ptxt = " ".join(map(str, params))
    L.append(f"    static final String BT{u}_PARAM_S =")
    for lit in chunk_strings(ptxt.split(" "), 2000):
        L.append("        " + ' "' + " ".join([])  + '"' )  # placeholder, replaced below
    L.pop()  # rebuild param emission properly below
    L.pop()
    # param: one literal is enough (~2000 numbers * 7 chars ≈ 14KB)
    L.append(f'    static final String BT{u}_PARAM_S =')
    L.append('        "' + ptxt + '";')
    # nodes: hex, 16 chars per node, chunk 3000 nodes = 48000 chars per literal;
    # joined via cat(...) at runtime so javac cannot constant-fold them together
    hexstr = "".join(nodes)
    L.append(f"    static final String BT{u}_NODES_S = cat(")
    lits = chunk_strings(hexstr, 48000)
    for i, lit in enumerate(lits):
        comma = "" if i == len(lits) - 1 else ","
        L.append("        " + lit + comma)
    L.append("    );")
    return "\n".join(L)

def main():
    blocks = [emit(t) for t in ("18", "192", "19", "20", "21wd")]
    helpers = """
    /** 拼接分块字符串 (阻止 javac 常量折叠, 规避常量池 64KB 限制)。 */
    static String cat(String... ss) {
        StringBuilder b = new StringBuilder();
        for (String s : ss) b.append(s);
        return b.toString();
    }

    /** 解码空白分隔的 int 表 (由 tools/convert_btree.py 生成)。 */
    static int[] decodeInts(String s) {
        String[] parts = s.trim().split("\\\\s+");
        int[] a = new int[parts.length];
        for (int i = 0; i < parts.length; i++) a[i] = Integer.parseInt(parts[i]);
        return a;
    }

    /** 解码 16 字符/节点的 hex 表 (由 tools/convert_btree.py 生成)。 */
    static long[] decodeHex(String s) {
        int n = s.length() / 16;
        long[] a = new long[n];
        for (int i = 0; i < n; i++)
            a[i] = Long.parseUnsignedLong(s.substring(i * 16, i * 16 + 16), 16);
        return a;
    }
"""
    tables = "\n".join(blocks) + "\n" + helpers
    java = OUT.read_text(encoding="utf-8")
    i0 = java.index(START)
    i1 = java.index(END)
    java = java[:i0] + tables + "\n" + java[i1:]
    for u in ("18", "192", "19", "20", "21WD"):
        java = java.replace(f"BT{u}_PARAM,", f"decodeInts(BT{u}_PARAM_S),")
        java = java.replace(f"BT{u}_NODES,", f"decodeHex(BT{u}_NODES_S),")
    OUT.write_text(java, encoding="utf-8")
    print(f"OK: spliced 5 btree tables (string-encoded) into {OUT.name}")

if __name__ == "__main__":
    main()
