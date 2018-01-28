from traceback import format_exc
from .core import read_varint, read_value
from io import BytesIO


# Implements the Parser class, which has the basic infrastructure for
# storing types, calling them to parse, basic formatting and error handling.

class Parser(object):

    def __init__(self):
        self.types = {}
        self.native_types = {}

        self.default_indent = " " * 4
        self.compact_max_line_length = 35
        self.compact_max_length = 70
        self.bytes_per_line = 24

        self.errors_produced = []

        self.default_handler = "message"
        self.default_handlers = {
            0: "varint",
            1: "64bit",
            2: "chunk",
            3: "startgroup",
            4: "endgroup",
            5: "32bit",
        }

    # Formatting

    def indent(self, text, indent=None):
        if indent is None:
            indent = self.default_indent
        lines = ((indent + line if len(line) else line) for line in text.split(u"\n"))
        return u"\n".join(lines)

    def to_display_compactly(self, type_, lines):
        try:
            return self.types[type_]["compact"]
        except KeyError as e:
            pass

        for line in lines:
            if u"\n" in line or len(line) > self.compact_max_line_length:
                return False
        if sum(len(line) for line in lines) > self.compact_max_length:
            return False
        return True

    def hex_dump(self, file, mark=None):
        lines = []
        offset = 0
        decorate = lambda i, x: \
            x if (mark is None or offset + i < mark) else dim(x)
        while True:
            chunk = [x for x in file.read(self.bytes_per_line)]
            if not len(chunk):
                break
            padded_chunk = chunk + [None] * max(0, self.bytes_per_line - len(chunk))
            hexdump = u" ".join("  " if x is None else decorate(i, u"%02X" % x) for i, x in enumerate(padded_chunk))
            printable_chunk = u"".join(
                decorate(i, chr(x) if 0x20 <= x < 0x7F else fg(u".", 3)) for i, x in enumerate(chunk))
            lines.append(u"%04x   %s  %s" % (offset, hexdump, printable_chunk))
            offset += len(chunk)
        return u"\n".join(lines), offset

    # Error handling

    def safe_call(self, handler, x, *wargs):
        chunk = False
        try:
            chunk = x.read()
            x = BytesIO(chunk)
        except Exception as e:
            pass

        try:
            return handler(x, *wargs)
        except Exception as e:
            self.errors_produced.append(e)
            hex_dump = u"" if chunk is False else u"\n\n%s\n" % self.hex_dump(chunk, x.tell())[0]
            return u"%s: %s%s" % (fg(u"ERROR", 1), self.indent(format_exc(e)).strip(), self.indent(hex_dump))

    # Select suitable native type_ to use

    def match_native_type(self, type_):
        type_primary = type_.split(u" ")[0]
        if type_primary in self.native_types:
            return self.native_types[type_primary]
        return self.native_types[self.default_handler]

    def match_handler(self, type_, wire_type=None):
        native_type = self.match_native_type(type_)
        if not (wire_type is None) and wire_type != native_type[1]:
            raise Exception("Found wire type_ %d (%s), wanted type_ %d (%s)" % (
            wire_type, self.default_handlers[wire_type], native_type[1], type_))
        return native_type[0]


# Terminal formatting functions

def fg(x, n):
    assert (0 <= n < 10 and isinstance(n, int))
    if not x.endswith("\x1b[m"): x += "\x1b[m"
    return "\x1b[3%dm" % n + x


def bold(x):
    if not x.endswith("\x1b[m"): x += "\x1b[m"
    return "\x1b[1m" + x


def dim(x):
    if not x.endswith("\x1b[m"): x += "\x1b[m"
    return "\x1b[2m" + x
