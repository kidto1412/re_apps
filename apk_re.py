#!/usr/bin/env python3
# Language: Python 3.8+
# Target: Android APK Static Reverse Engineering & Inspection Engine

import os
import sys
import struct
import zipfile
import hashlib
import argparse
from typing import List, Dict, Any, Optional, Tuple

CHUNK_AXML_FILE = 0x00080003
CHUNK_STRING_POOL = 0x001C0001
CHUNK_RESOURCEIDS = 0x00080180
CHUNK_XML_START_NAMESPACE = 0x00100100
CHUNK_XML_END_NAMESPACE = 0x00100101
CHUNK_XML_START_TAG = 0x00100102
CHUNK_XML_END_TAG = 0x00100103
CHUNK_XML_TEXT = 0x00100104


class BinaryAXMLParser:
    """Parses binary AndroidManifest.xml without external dependencies."""

    def __init__(self, data: bytes):
        self.raw = data
        self.cursor = 0
        self.strings: List[str] = []
        self.xml_lines: List[str] = []
        self.indent = 0
        self.package_name = ""
        self.permissions: List[str] = []
        self.components: Dict[str, List[str]] = {
            "activities": [],
            "services": [],
            "receivers": [],
            "providers": []
        }

    def _read_u16(self) -> int:
        val = struct.unpack_from("<H", self.raw, self.cursor)[0]
        self.cursor += 2
        return val

    def _read_u32(self) -> int:
        val = struct.unpack_from("<I", self.raw, self.cursor)[0]
        self.cursor += 4
        return val

    def parse(self) -> str:
        if self.xml_lines:
            return "\n".join(self.xml_lines)
        if len(self.raw) < 8:
            return ""

        self.cursor = 0
        file_type = self._read_u32()
        if file_type != CHUNK_AXML_FILE:
            return ""

        _file_size = self._read_u32()

        while self.cursor + 8 <= len(self.raw):
            chunk_start = self.cursor
            chunk_type = self._read_u32()
            chunk_size = self._read_u32()
            if chunk_size < 8:
                break

            if chunk_type == CHUNK_STRING_POOL:
                self._parse_string_pool(chunk_start, chunk_size)
            elif chunk_type == CHUNK_XML_START_TAG:
                self._parse_start_tag()
            elif chunk_type == CHUNK_XML_END_TAG:
                self._parse_end_tag()

            self.cursor = chunk_start + chunk_size

        return "\n".join(self.xml_lines)

    def _parse_string_pool(self, chunk_start: int, chunk_size: int):
        string_count = self._read_u32()
        _style_count = self._read_u32()
        flags = self._read_u32()
        strings_start = chunk_start + self._read_u32()
        _styles_start = self._read_u32()

        is_utf8 = bool(flags & (1 << 8))
        offsets = [self._read_u32() for _ in range(string_count)]

        self.strings = []
        for off in offsets:
            str_ptr = strings_start + off
            if str_ptr >= len(self.raw):
                self.strings.append("")
                continue

            if is_utf8:
                # UTF-8 encoded
                u16len = self.raw[str_ptr]
                str_ptr += 1
                if u16len & 0x80:
                    str_ptr += 1
                u8len = self.raw[str_ptr]
                str_ptr += 1
                if u8len & 0x80:
                    u8len = ((u8len & 0x7F) << 8) | self.raw[str_ptr]
                    str_ptr += 1
                s = self.raw[str_ptr : str_ptr + u8len].decode("utf-8", errors="replace")
            else:
                # UTF-16LE encoded
                u16len = struct.unpack_from("<H", self.raw, str_ptr)[0]
                str_ptr += 2
                if u16len & 0x8000:
                    u16len = ((u16len & 0x7FFF) << 16) | struct.unpack_from("<H", self.raw, str_ptr)[0]
                    str_ptr += 2
                raw_bytes = self.raw[str_ptr : str_ptr + (u16len * 2)]
                s = raw_bytes.decode("utf-16le", errors="replace")

            self.strings.append(s)

    def _get_string(self, idx: int) -> str:
        if 0 <= idx < len(self.strings):
            return self.strings[idx]
        return ""

    def _parse_start_tag(self):
        _line_num = self._read_u32()
        _comment = self._read_u32()
        _ns = self._read_u32()
        name_idx = self._read_u32()
        _flags = self._read_u32()
        attr_count = self._read_u16()
        _id_idx = self._read_u16()
        _class_idx = self._read_u16()
        _style_idx = self._read_u16()

        tag_name = self._get_string(name_idx)
        attrs = []

        for _ in range(attr_count):
            _attr_ns = self._read_u32()
            attr_name_idx = self._read_u32()
            attr_raw_val_idx = self._read_u32()
            _attr_type = self._read_u32() >> 24
            attr_data = self._read_u32()

            attr_name = self._get_string(attr_name_idx)
            val = self._get_string(attr_raw_val_idx) if attr_raw_val_idx != 0xFFFFFFFF else str(attr_data)
            attrs.append((attr_name, val))

            if tag_name == "manifest" and attr_name == "package":
                self.package_name = val
            elif tag_name == "uses-permission" and attr_name == "name":
                self.permissions.append(val)
            elif attr_name == "name":
                if tag_name == "activity":
                    self.components["activities"].append(val)
                elif tag_name == "service":
                    self.components["services"].append(val)
                elif tag_name == "receiver":
                    self.components["receivers"].append(val)
                elif tag_name == "provider":
                    self.components["providers"].append(val)

        attr_str = " ".join([f'{k}="{v}"' for k, v in attrs])
        indent_str = "  " * self.indent
        self.xml_lines.append(f"{indent_str}<{tag_name}{(' ' + attr_str) if attr_str else ''}>")
        self.indent += 1

    def _parse_end_tag(self):
        _line_num = self._read_u32()
        _comment = self._read_u32()
        _ns = self._read_u32()
        name_idx = self._read_u32()
        tag_name = self._get_string(name_idx)
        self.indent = max(0, self.indent - 1)
        indent_str = "  " * self.indent
        self.xml_lines.append(f"{indent_str}</{tag_name}>")


class DEXParser:
    """Parses Dalvik Executable (DEX) bytecode headers and string tables."""

    def __init__(self, data: bytes):
        self.raw = data
        self.strings: List[str] = []
        self.types: List[str] = []
        self.classes: List[str] = []

    def _read_uleb128(self, offset: int) -> Tuple[int, int]:
        result = 0
        shift = 0
        size = 0
        while True:
            byte = self.raw[offset + size]
            size += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result, size

    def parse(self):
        if len(self.raw) < 0x70:
            return

        magic = self.raw[0:8]
        if not (magic.startswith(b"dex\n") and magic.endswith(b"\0")):
            return

        (string_ids_size, string_ids_off) = struct.unpack_from("<II", self.raw, 0x38)
        (type_ids_size, type_ids_off) = struct.unpack_from("<II", self.raw, 0x40)
        (class_defs_size, class_defs_off) = struct.unpack_from("<II", self.raw, 0x60)

        # Parse Strings
        for i in range(string_ids_size):
            str_data_off = struct.unpack_from("<I", self.raw, string_ids_off + (i * 4))[0]
            _utf16_size, leb_len = self._read_uleb128(str_data_off)
            content_start = str_data_off + leb_len
            null_pos = self.raw.find(b"\0", content_start)
            if null_pos != -1:
                decoded = self.raw[content_start:null_pos].decode("utf-8", errors="replace")
                self.strings.append(decoded)
            else:
                self.strings.append("")

        # Parse Types
        for i in range(type_ids_size):
            descriptor_idx = struct.unpack_from("<I", self.raw, type_ids_off + (i * 4))[0]
            if descriptor_idx < len(self.strings):
                self.types.append(self.strings[descriptor_idx])

        # Parse Class Definitions
        for i in range(class_defs_size):
            class_idx = struct.unpack_from("<I", self.raw, class_defs_off + (i * 32))[0]
            if class_idx < len(self.types):
                raw_type = self.types[class_idx]
                if raw_type.startswith("L") and raw_type.endswith(";"):
                    formatted = raw_type[1:-1].replace("/", ".")
                else:
                    formatted = raw_type
                self.classes.append(formatted)


class APKAnalyzer:
    """Main reverse engineering interface for inspecting Android APK binaries."""

    def __init__(self, apk_path: str):
        self.apk_path = os.path.abspath(apk_path)
        if not os.path.isfile(self.apk_path):
            raise FileNotFoundError(f"Target not found: {self.apk_path}")

        self.zip_ref = zipfile.ZipFile(self.apk_path, "r")
        self.namelist = self.zip_ref.namelist()
        self.manifest: Optional[BinaryAXMLParser] = None
        self.dex_parsers: List[DEXParser] = []
        self._analyze()

    def _analyze(self):
        # Parse Manifest
        if "AndroidManifest.xml" in self.namelist:
            raw_manifest = self.zip_ref.read("AndroidManifest.xml")
            self.manifest = BinaryAXMLParser(raw_manifest)
            self.manifest.parse()

        # Parse all classes*.dex
        dex_files = [f for f in self.namelist if f.startswith("classes") and f.endswith(".dex")]
        for df in sorted(dex_files):
            raw_dex = self.zip_ref.read(df)
            parser = DEXParser(raw_dex)
            parser.parse()
            self.dex_parsers.append(parser)

    def get_summary(self) -> Dict[str, Any]:
        with open(self.apk_path, "rb") as f:
            content = f.read()
            sha256 = hashlib.sha256(content).hexdigest()
            md5 = hashlib.md5(content).hexdigest()

        native_libs: Dict[str, List[str]] = {}
        for entry in self.namelist:
            if entry.startswith("lib/") and entry.endswith(".so"):
                parts = entry.split("/")
                if len(parts) >= 3:
                    arch = parts[1]
                    so_name = parts[2]
                    native_libs.setdefault(arch, []).append(so_name)

        total_classes = sum(len(p.classes) for p in self.dex_parsers)
        total_strings = sum(len(p.strings) for p in self.dex_parsers)

        return {
            "file_name": os.path.basename(self.apk_path),
            "file_size_bytes": os.path.getsize(self.apk_path),
            "md5": md5,
            "sha256": sha256,
            "package_name": self.manifest.package_name if self.manifest else "Unknown",
            "dex_count": len(self.dex_parsers),
            "total_classes": total_classes,
            "total_strings": total_strings,
            "native_architectures": list(native_libs.keys()),
            "native_libraries": native_libs,
            "permissions_count": len(self.manifest.permissions) if self.manifest else 0,
        }

    def get_classes(self) -> List[str]:
        classes = []
        for parser in self.dex_parsers:
            classes.extend(parser.classes)
        return sorted(list(set(classes)))

    def get_strings(self, min_len: int = 4) -> List[str]:
        strings = set()
        for parser in self.dex_parsers:
            for s in parser.strings:
                if len(s) >= min_len and any(c.isalnum() for c in s):
                    strings.add(s)
        return sorted(list(strings))

    def extract_all(self, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        self.zip_ref.extractall(output_dir)

        if self.manifest:
            manifest_out = os.path.join(output_dir, "AndroidManifest_decoded.xml")
            with open(manifest_out, "w", encoding="utf-8") as f:
                f.write(self.manifest.parse())


def main():
    parser = argparse.ArgumentParser(
        description="APK Static Reverse Engineering and Analysis Engine"
    )
    parser.add_argument("apk", help="Path to the .apk target file")
    parser.add_argument("-i", "--info", action="store_true", help="Display metadata & binary overview")
    parser.add_argument("-p", "--permissions", action="store_true", help="List declared permissions")
    parser.add_argument("-c", "--classes", action="store_true", help="Dump recovered class names")
    parser.add_argument("-s", "--strings", action="store_true", help="Dump strings pool from Dalvik bytecode")
    parser.add_argument("-m", "--manifest", action="store_true", help="Print reconstructed AndroidManifest.xml")
    parser.add_argument("-x", "--extract", metavar="DIR", help="Extract raw archive and decoded manifest to directory")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    engine = APKAnalyzer(args.apk)

    if args.info or not (args.permissions or args.classes or args.strings or args.manifest or args.extract):
        info = engine.get_summary()
        print(f"[*] Target:          {info['file_name']}")
        print(f"[*] Package:         {info['package_name']}")
        print(f"[*] Size:            {info['file_size_bytes']:,} bytes")
        print(f"[*] SHA-256:         {info['sha256']}")
        print(f"[*] MD5:             {info['md5']}")
        print(f"[*] DEX Files:       {info['dex_count']}")
        print(f"[*] Total Classes:   {info['total_classes']:,}")
        print(f"[*] Total Strings:   {info['total_strings']:,}")
        print(f"[*] Native ABIs:     {', '.join(info['native_architectures']) or 'None (Pure Java/Kotlin)'}")
        if info["native_libraries"]:
            for arch, libs in info["native_libraries"].items():
                print(f"    - [{arch}]: {', '.join(libs)}")
        print(f"[*] Permissions:     {info['permissions_count']}")

    if args.permissions and engine.manifest:
        print("\n--- Declared Permissions ---")
        for perm in sorted(set(engine.manifest.permissions)):
            print(f"  + {perm}")

    if args.manifest and engine.manifest:
        print("\n--- AndroidManifest.xml (Decoded) ---")
        print(engine.manifest.parse())

    if args.classes:
        print("\n--- Recovered Class Definitions ---")
        for cls in engine.get_classes():
            print(cls)

    if args.strings:
        print("\n--- Dalvik Bytecode Strings ---")
        for s in engine.get_strings():
            print(s)

    if args.extract:
        engine.extract_all(args.extract)
        print(f"\n[+] Extracted APK container and decoded manifest to: {args.extract}")


if __name__ == "__main__":
    main()
