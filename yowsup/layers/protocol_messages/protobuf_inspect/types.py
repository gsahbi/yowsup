from .core import read_varint, read_value
from .parser import Parser, fg, dim, bold
from struct import unpack
from io import BytesIO


# Code that implements and registers the usual native types (high
# level parsing and formatting) into the barebones Parser.

class StandardParser(Parser):

    def __init__(self):
        super(StandardParser, self).__init__()

        self.types["message"] = {}

        self.message_compact_max_lines = 4
        self.packed_compact_max_lines = 20

        self.dump_prefix = "dump."
        self.dump_index = 0

        types_to_register = {
            0: ["varint", "sint32", "sint64", "int32", "int64", "uint32", "uint64", "enum"],
            1: ["64bit", "sfixed64", "fixed64", "double"],
            2: ["chunk", "bytes", "string", "message", "packed", "dump"],
            5: ["32bit", "sfixed32", "fixed32", "float"],
        }
        for wire_type, types in types_to_register.items():
            for type_ in types:
                self.native_types[type_] = (getattr(self, "parse_" + type_), wire_type)

    # This is the function that handles any non-native type_.

    def get_message_field_entry(self, gtype, key):
        type_ = None
        field = None
        try:
            field_entry = self.types[gtype][key]
            if not isinstance(field_entry, tuple): field_entry = (field_entry,)
            type_ = field_entry[0]
            field = field_entry[1]
        except KeyError as e:
            pass
        except IndexError as e:
            pass
        return type_, field

    def parse_message(self, file, gtype, endgroup=None):
        if gtype not in self.types and gtype != self.default_handler:
            raise Exception("Unknown message type_ %s" % gtype)

        lines = []
        while True:
            key = read_varint(file)
            if key is None:
                break

            wire_type = key & 0x07
            key = key >> 3
            x = read_value(file, wire_type)
            assert (not (x is None))

            if wire_type is 4: break

            type_, field = self.get_message_field_entry(gtype, key)
            if type_ is None:
                type_ = self.default_handlers[wire_type]
            if wire_type is 3:
                x = self.parse_message(file, type_, key)
            else:
                handler = self.match_handler(type_, wire_type)
                x = self.safe_call(lambda x_: handler(x_, type_), x)

            if field is None: field = u"<%s>" % type_
            lines.append(u"%s %s = %s" % (fg(str(key), 4), field, x))

        assert (endgroup == key)
        if len(lines) <= self.message_compact_max_lines and self.to_display_compactly(gtype, lines):
            return u"%s(%s)" % (gtype, u", ".join(lines))
        if not len(lines): lines = [u"empty"]
        return u"%s:\n%s" % (gtype, self.indent(u"\n".join(lines)))

    # Functions for generic types (default for wire types)

    def parse_varint(self, x, type_):
        result = [x]
        if (1 << 64) - 20000 <= x < (1 << 64):
            # Would be small and negative if interpreted as int32 / int64
            result.insert(0, x - (1 << 64))

        s = fg(u"%d" % result[0], 3)
        if len(result) >= 2:
            s += " (%d)" % result[1]
        return s

    def is_probable_string(self, string):
        controlchars = 0
        alnum = 0
        total = len(string)
        for c in string:
            c = ord(c)
            if c < 0x20 or c == 0x7F:
                controlchars += 1
            if (ord(u"A") <= c <= ord(u"Z")) or (ord(u"a") <= c <= ord(u"z")) or (
                    ord(u"0") <= c <= ord(u"9")): alnum += 1

        if controlchars / float(total) > 0.1:
            return False
        if alnum / float(total) < 0.5:
            return False
        return True

    def parse_chunk(self, file, type_):
        chunk = file.read()
        if len(chunk) is 0:
            return "empty chunk"

        # Attempt to decode message
        try:
            return self.parse_message(BytesIO(chunk), "message")
        except Exception as e:
            pass

        # Attempt to decode packed repeated chunks
        try:
            if len(chunk) >= 5:
                return self.parse_packed(BytesIO(chunk), "packed chunk")
        except Exception as e:
            pass

        # Attempt to decode as UTF-8
        try:
            if self.is_probable_string(chunk.decode("utf-8")):
                return self.parse_string(BytesIO(chunk), "string")
        except UnicodeError as e:
            pass

        # Fall back to hexdump
        return self.parse_bytes(BytesIO(chunk), "bytes")

    def parse_32bit(self, x, type_):
        signed = unpack("<i", x)[0]
        unsigned = unpack("<I", x)[0]
        floating = unpack("<f", x)[0]
        return "0x%08X / %d / %#g" % (unsigned, signed, floating)

    def parse_64bit(self, x, type_):
        signed = unpack("<q", x)[0]
        unsigned = unpack("<Q", x)[0]
        floating = unpack("<d", x)[0]
        return "0x%016X / %d / %#.8g" % (unsigned, signed, floating)

    # Functions for protobuf types

    def parse_sint32(self, x, type_):
        assert (0 <= x < (1 << 32))
        return fg(str(zigzag(x)), 3)

    def parse_sint64(self, x, type_):
        assert (0 <= x < (1 << 64))
        return fg(str(zigzag(x)), 3)

    def parse_int32(self, x, type_):
        assert (0 <= x < (1 << 64))
        if x >= (1 << 63): x -= (1 << 64)
        assert (-(1 << 31) <= x < (1 << 31))
        return fg(str(x), 3)

    def parse_int64(self, x, type_):
        assert (0 <= x < (1 << 64))
        if x >= (1 << 63): x -= (1 << 64)
        return fg(str(x), 3)

    def parse_uint32(self, x, type_):
        assert (0 <= x < (1 << 32))
        return fg(str(x), 3)

    def parse_uint64(self, x, type_):
        assert (0 <= x < (1 << 64))
        return fg(str(x), 3)

    def parse_string(self, file, type_):
        string = file.read().decode("utf-8")
        return fg('"%s"' % (repr(string)[1:-1]), 2)

    def parse_bytes(self, file, type_):
        hex_dump, offset = self.hex_dump(file)
        return u"%s (%d)\n%s" % (type_, offset, self.indent(hex_dump))

    def parse_packed(self, file, gtype):
        assert (gtype.startswith("packed "))
        type_ = gtype[7:]
        handler, wire_type = self.match_native_type(type_)

        lines = []
        while True:
            x = read_value(file, wire_type)
            if x is None:
                break
            lines.append(self.safe_call(handler, x, type_))

        if len(lines) <= self.packed_compact_max_lines and self.to_display_compactly(gtype, lines):
            return u"[%s]" % (", ".join(lines))
        return u"packed:\n%s" % (self.indent(u"\n".join(lines)))

    def parse_fixed32(self, x, type_):
        return fg("%d" % unpack("<i", x)[0], 2)

    def parse_sfixed32(self, x, type_):
        return fg("%d" % unpack("<I", x)[0], 2)

    def parse_float(self, x, type_):
        return fg("%#g" % unpack("<f", x)[0], 2)

    def parse_fixed64(self, x, type_):
        return fg("%d" % unpack("<q", x)[0], 2)

    def parse_sfixed64(self, x, type_):
        return fg("%d" % unpack("<Q", x)[0], 2)

    def parse_double(self, x, type_):
        return fg("%#.8g" % unpack("<d", x)[0], 2)

    def parse_enum(self, x, type_):
        if type_ not in self.types:
            raise Exception("Enum type_ '%s' not defined" % type_)
        type_entry = self.types[type_]
        if x not in type_entry:
            raise Exception("Unknown value %d for '%s'" % (x, type_))
        return fg(type_entry[x], 6)

    # Other convenience types

    def parse_dump(self, file, type_):
        chunk = file.read()
        filename = self.dump_prefix + str(self.dump_index)
        file = open(filename, "w")
        file.write(chunk)
        file.close()
        self.dump_index += 1
        return "%d bytes written to %s" % (len(chunk), filename)


def zigzag(x):
    negative = x & 1
    x = x >> 1
    return -(x + 1) if negative else x
