"""Text from old Word 97-2003 .doc files (pure Python, works on Streamlit Cloud).

Reads the piece table (Clx) from the table stream and pulls each text piece from the WordDocument stream,
8-bit (cp1252) or UTF-16 as the piece says. Spec: [MS-DOC] 2.5.1 (FIB), 2.9.38 (Clx), 2.9.177 (Pcd).
"""
import io
import re
import struct

import olefile


def doc_text(data: bytes) -> str:
    ole = olefile.OleFileIO(io.BytesIO(data))
    word = ole.openstream("WordDocument").read()
    flags = struct.unpack_from("<H", word, 0x0A)[0]
    table_name = "1Table" if flags & 0x0200 else "0Table"
    table = ole.openstream(table_name).read()
    fc_clx, lcb_clx = struct.unpack_from("<II", word, 0x01A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i = 0
    while i < len(clx) and clx[i] == 0x01:  # skip Prc entries
        i += 3 + struct.unpack_from("<H", clx, i + 1)[0]
    if i >= len(clx) or clx[i] != 0x02:
        raise ValueError("no piece table")
    lcb = struct.unpack_from("<I", clx, i + 1)[0]
    plc = clx[i + 5:i + 5 + lcb]
    n = (lcb - 4) // 12
    cps = struct.unpack_from(f"<{n + 1}I", plc, 0)
    out = []
    for k in range(n):
        fc = struct.unpack_from("<I", plc, 4 * (n + 1) + 8 * k + 2)[0]
        chars = cps[k + 1] - cps[k]
        if fc & 0x40000000:
            start = (fc & ~0x40000000) // 2
            out.append(word[start:start + chars].decode("cp1252", errors="replace"))
        else:
            out.append(word[fc:fc + 2 * chars].decode("utf-16-le", errors="replace"))
    text = "".join(out)
    text = text.replace("\r", "\n").replace("\x07", "\t").replace("\x0b", "\n").replace("\x0c", "\n")
    text = re.sub(r"\x13[^\x14\x15]*\x14", "", text)       # field codes: keep only the shown result
    text = re.sub(r"[\x00-\x08\x0e-\x1f\x13\x14\x15]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


if __name__ == "__main__":
    import sys
    print(doc_text(open(sys.argv[1], "rb").read())[:3000])
