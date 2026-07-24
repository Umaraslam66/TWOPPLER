"""Stream-extract news_dialogue.json from a deflate64 (method 9) zip.

macOS unzip/ditto/bsdtar and Python's stdlib zipfile cannot decode ZIP
compression method 9 (deflate64). We read the raw compressed stream out of
the local file header and feed it to the `inflate64` decompressor in chunks,
writing the plaintext straight to disk so peak memory stays tiny.

Run: .venv/bin/python experiments/extract_deflate64.py
"""
import struct
import sys
import time
import zipfile

import inflate64

ZIP = "/Users/umaraslam/Projects/DOPPLER/data/mediasum/mediasum.zip"
OUT = "/Users/umaraslam/Projects/DOPPLER/data/mediasum/news_dialogue.json"
MEMBER = "news_dialogue.json"


def main():
    t0 = time.time()
    with zipfile.ZipFile(ZIP) as zf:
        info = zf.getinfo(MEMBER)
    assert info.compress_type == 9, f"expected deflate64 (9), got {info.compress_type}"

    with open(ZIP, "rb") as fz:
        fz.seek(info.header_offset)
        local = fz.read(30)
        assert local[:4] == b"PK\x03\x04", "bad local header signature"
        fname_len = struct.unpack("<H", local[26:28])[0]
        extra_len = struct.unpack("<H", local[28:30])[0]
        data_start = info.header_offset + 30 + fname_len + extra_len
        fz.seek(data_start)

        remaining = info.compress_size
        infl = inflate64.Inflater()
        written = 0
        chunk = 16 * 1024 * 1024
        with open(OUT, "wb") as fo:
            while remaining > 0:
                buf = fz.read(min(chunk, remaining))
                if not buf:
                    break
                remaining -= len(buf)
                out = infl.inflate(buf)
                if out:
                    fo.write(out)
                    written += len(out)
    dt = time.time() - t0
    print(f"wrote {written} bytes to {OUT} in {dt:.1f}s "
          f"(expected {info.file_size})")
    if written != info.file_size:
        print("WARNING: size mismatch vs zip directory", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
