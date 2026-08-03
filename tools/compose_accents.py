"""Compose missing accented letters for ETBook UFOs from base + accent.

The font's existing accented letters are independent drawings, so exact
point-reuse is impossible.  Instead we derive each accent's placement
convention from the exemplars geometrically: contours sitting entirely
above the base letter are the accent part; we record the accent band's
bottom y and the horizontal offset of the accent's center from the base
part's center.  New letters are then composed from the base glyph plus
the standalone accent glyph placed by those conventions.
"""
import os
import plistlib
import sys

from fontTools.ufoLib.glifLib import GlyphSet

REPO = "/Users/milo/ws/personal/et-book"


class G:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.unicodes = []
        self.contours = []

    def drawPoints(self, pen):
        for c in self.contours:
            pen.beginPath()
            for x, y, t, s in c:
                pen.addPoint((x, y), segmentType=t, smooth=s)
            pen.endPath()


class Collector:
    def __init__(self, g):
        self.g = g
        self.cur = None

    def beginPath(self, identifier=None, **k):
        self.cur = []

    def addPoint(self, pt, segmentType=None, smooth=False, **k):
        self.cur.append((pt[0], pt[1], segmentType, smooth))

    def endPath(self):
        self.g.contours.append(self.cur)
        self.cur = None

    def addComponent(self, *a, **k):
        raise ValueError("component in %s" % self.g)


def cbox(cont):
    xs = [p[0] for p in cont]
    ys = [p[1] for p in cont]
    return min(xs), min(ys), max(xs), max(ys)


def gbox(contours):
    bs = [cbox(c) for c in contours]
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def cx(b):
    return (b[0] + b[2]) / 2.0


class Face:
    def __init__(self, face):
        self.face = face
        self.gs = GlyphSet(os.path.join(REPO, f"ufo/ETBook-{face}.ufo/glyphs"),
                           ufoFormatVersion=3)

    def read(self, name):
        g = G()
        self.gs.readGlyph(name, g, Collector(g))
        return g

    def has(self, name):
        return name in self.gs.contents

    def split(self, exemplar, base):
        """Split exemplar contours into (base part, accent part)."""
        ex = self.read(exemplar)
        bb = gbox(self.read(base).contours)
        base_top = bb[3]
        acc, rest = [], []
        for c in ex.contours:
            (acc if cbox(c)[1] > base_top - 30 else rest).append(c)
        return rest, acc

    def derive(self, accent, exemplars):
        """Median accent-bottom y and horizontal center delta."""
        ys, deltas = [], []
        for exemplar, base in exemplars:
            if not (self.has(exemplar) and self.has(base)):
                continue
            rest, acc = self.split(exemplar, base)
            if not acc or not rest:
                continue
            ab, rb = gbox(acc), gbox(rest)
            ys.append(ab[1])
            deltas.append(cx(ab) - cx(rb))
        if not ys:
            return None
        ys.sort(); deltas.sort()
        return dict(y=ys[len(ys) // 2], delta=deltas[len(deltas) // 2],
                    n=len(ys))

    def compose(self, name, unicode_, base, accent, conv, dry=False):
        b = self.read(base)
        a = self.read(accent)
        abb = gbox(a.contours)
        bbb = gbox(b.contours)
        dy = conv["y"] - abb[1]
        dx = (cx(bbb) + conv["delta"]) - cx(abb)
        dx = round(dx); dy = round(dy)
        g = G()
        g.width = b.width
        g.unicodes = [unicode_]
        g.contours = [list(c) for c in b.contours] + [
            [(x + dx, y + dy, t, s) for x, y, t, s in c] for c in a.contours]
        if not dry:
            self.gs.writeGlyph(name, g, g.drawPoints)
        return g


# exemplar tables (glif names; capitals use the UFO underscore names)
EX = {
    "acute.lc": ("acute", [("aacute", "a"), ("eacute", "e"), ("oacute", "o"),
                           ("uacute", "u"), ("yacute", "y")]),
    "acute.uc": ("acute", [("Aacute", "A"), ("Eacute", "E"),
                           ("Oacute", "O"), ("Uacute", "U"),
                           ("Yacute", "Y")]),
    "caron.lc": ("caron", [("scaron", "s"), ("zcaron", "z")]),
    "caron.uc": ("caron", [("Scaron", "S"), ("Zcaron", "Z")]),
    "dieresis.lc": ("dieresis", [("adieresis", "a"), ("edieresis", "e"),
                                 ("odieresis", "o"), ("udieresis", "u")]),
    "dieresis.uc": ("dieresis", [("Adieresis", "A"), ("Odieresis", "O"),
                                 ("Udieresis", "U")]),
    "ring.lc": ("ring", [("aring", "a")]),
    "ring.uc": ("ring", [("Aring", "A")]),
}

# what to build: name, unicode, base, accent, convention key
# (fallback convention key used when the primary has no exemplars)
NEW = [
    ("cacute",      0x0107, "c",  "acute",        "acute.lc"),
    ("Cacute",     0x0106, "C", "acute",        "acute.uc"),
    ("nacute",      0x0144, "n",  "acute",        "acute.lc"),
    ("Nacute",     0x0143, "N", "acute",        "acute.uc"),
    ("sacute",      0x015A + 1, "s", "acute",     "acute.lc"),
    ("Sacute",     0x015A, "S", "acute",        "acute.uc"),
    ("zacute",      0x017A, "z",  "acute",        "acute.lc"),
    ("Zacute",     0x0179, "Z", "acute",        "acute.uc"),
    ("ccaron",      0x010D, "c",  "caron",        "caron.lc"),
    ("Ccaron",     0x010C, "C", "caron",        "caron.uc"),
    ("ecaron",      0x011B, "e",  "caron",        "caron.lc"),
    ("Ecaron",     0x011A, "E", "caron",        "caron.uc"),
    ("ncaron",      0x0148, "n",  "caron",        "caron.lc"),
    ("Ncaron",     0x0147, "N", "caron",        "caron.uc"),
    ("rcaron",      0x0159, "r",  "caron",        "caron.lc"),
    ("Rcaron",     0x0158, "R", "caron",        "caron.uc"),
    ("zdotaccent",  0x017C, "z",  "dotaccent",    "dieresis.lc"),
    ("Zdotaccent", 0x017B, "Z", "dotaccent",    "dieresis.uc"),
    ("edotaccent",  0x0117, "e",  "dotaccent",    "dieresis.lc"),
    ("Edotaccent", 0x0116, "E", "dotaccent",    "dieresis.uc"),
    ("umacron",     0x016B, "u",  "macron",       "dieresis.lc"),
    ("Umacron",    0x016A, "U", "macron",       "dieresis.uc"),
    ("uring",       0x016F, "u",  "ring",         "ring.lc"),
    ("Uring",      0x016E, "U", "ring",         "ring.uc"),
    ("ohungarumlaut", 0x0151, "o",  "hungarumlaut", "acute.lc"),
    ("Ohungarumlaut", 0x0150, "O", "hungarumlaut", "acute.uc"),
    ("uhungarumlaut", 0x0171, "u",  "hungarumlaut", "acute.lc"),
    ("Uhungarumlaut", 0x0170, "U", "hungarumlaut", "acute.uc"),
]

GLYPHNAME = {  # glif -> glyph name for contents/glyphOrder
    n: n.replace("_", "") for n, *_ in NEW
}


def run(face_name, dry=False):
    face = Face(face_name)
    conv = {}
    for key, (accent, exemplars) in EX.items():
        if not face.has(accent):
            continue
        c = face.derive(accent, exemplars)
        if c:
            conv[key] = c
    print(f"[{face_name}] conventions:",
          {k: {kk: round(vv, 1) if isinstance(vv, float) else vv
               for kk, vv in v.items()} for k, v in conv.items()})
    made = []
    for glifname, uni, base, accent, key in NEW:
        gname = glifname.replace("_", "")
        if face.has(gname):
            print(f"  {gname}: already exists, skipped")
            continue
        if key not in conv or not face.has(accent) or not face.has(base):
            print(f"  {gname}: SKIP (no convention/parts)")
            continue
        g = face.compose(gname, uni, base, accent, conv[key], dry=dry)
        made.append(gname)
        print(f"  {gname}: U+{uni:04X} composed (advance {g.width})")
    if not dry and made:
        face.gs.writeContents()
        libp = os.path.join(REPO, f"ufo/ETBook-{face_name}.ufo/lib.plist")
        with open(libp, "rb") as f:
            lib = plistlib.load(f)
        order = lib.get("public.glyphOrder")
        if order:
            order.extend(n for n in made if n not in order)
            with open(libp, "wb") as f:
                plistlib.dump(lib, f)
    return made


if __name__ == "__main__":
    for face_name in sys.argv[1:] or ["Roman"]:
        run(face_name)
