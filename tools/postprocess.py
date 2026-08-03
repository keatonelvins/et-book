#!/usr/bin/env python3
"""Post-build fix-up for ET Book OTFs.

makeotf derives name records, style bits and vertical metrics that are
wrong or inconsistent for this family (five fonts all claiming
"ETBook Regular", no bold/italic style linking, per-face bbox-driven
vertical metrics).  This script rewrites the affected tables on the
compiled OTFs; the TTF/WOFF2 targets inherit the fixes because they are
derived from these files.

Usage: postprocess.py FONT.otf [FONT.otf ...]
"""
import math
import sys

from fontTools.ttLib import TTFont

VERSION = "2.000"
VENDOR = "ETBK"

# Family model: RIBBI family "ET Book" (Regular/Italic/Bold) plus the
# Semibold parked in its own legacy family, tied back to "ET Book" with
# typographic-family records (nameIDs 16/17) exactly like e.g.
# "Source Sans Pro Semibold".  DisplayItalic is kept buildable but named
# as its own "ET Book Display" family.
STYLES = {
    "ETBook-Roman": dict(
        family="ET Book", subfamily="Regular",
        weight=400, fs_selection=0x0040, mac_style=0x0000),
    "ETBook-Italic": dict(
        family="ET Book", subfamily="Italic",
        weight=400, fs_selection=0x0001, mac_style=0x0002,
        italic_angle=-11.8),
    "ETBook-Bold": dict(
        family="ET Book", subfamily="Bold",
        weight=700, fs_selection=0x0020, mac_style=0x0001),
    "ETBook-Semibold": dict(
        family="ET Book Semibold", subfamily="Regular",
        weight=600, fs_selection=0x0040, mac_style=0x0000,
        typo_family="ET Book", typo_subfamily="Semibold"),
    "ETBook-DisplayItalic": dict(
        family="ET Book Display", subfamily="Italic",
        weight=400, fs_selection=0x0001, mac_style=0x0002,
        italic_angle=-12.0),
}

# Family-wide vertical metrics (Roman's makeotf values, applied to every
# face so baselines and line boxes match when faces are mixed).  Win
# metrics are the family maxima so nothing clips on Windows.
TYPO_ASCENDER = 736
TYPO_DESCENDER = -264
TYPO_LINE_GAP = 200
WIN_ASCENT = 938
WIN_DESCENT = 289
USE_TYPO_METRICS = 0x0080


def set_name(name, string, name_id):
    name.setName(string, name_id, 3, 1, 0x409)
    name.setName(string, name_id, 1, 0, 0)


def remove_name(name, name_id):
    name.removeNames(nameID=name_id)


def process(path):
    font = TTFont(path)
    ps_name = font["name"].getDebugName(6)
    if ps_name not in STYLES:
        raise SystemExit(f"{path}: unknown PostScript name {ps_name!r}")
    style = STYLES[ps_name]
    family, subfamily = style["family"], style["subfamily"]
    full_name = family if subfamily == "Regular" else f"{family} {subfamily}"

    name = font["name"]
    set_name(name, family, 1)
    set_name(name, subfamily, 2)
    set_name(name, f"{VERSION};{VENDOR};{ps_name}", 3)
    set_name(name, full_name, 4)
    set_name(name, f"Version {VERSION}", 5)
    remove_name(name, 16)
    remove_name(name, 17)
    if "typo_family" in style:
        set_name(name, style["typo_family"], 16)
        set_name(name, style["typo_subfamily"], 17)

    os2 = font["OS/2"]
    os2.usWeightClass = style["weight"]
    os2.fsSelection = style["fs_selection"] | USE_TYPO_METRICS
    os2.achVendID = VENDOR
    os2.sTypoAscender = TYPO_ASCENDER
    os2.sTypoDescender = TYPO_DESCENDER
    os2.sTypoLineGap = TYPO_LINE_GAP
    os2.usWinAscent = WIN_ASCENT
    os2.usWinDescent = WIN_DESCENT

    head = font["head"]
    head.fontRevision = float(VERSION)
    head.macStyle = style["mac_style"]

    hhea = font["hhea"]
    hhea.ascent = TYPO_ASCENDER
    hhea.descent = TYPO_DESCENDER
    hhea.lineGap = TYPO_LINE_GAP

    angle = style.get("italic_angle", 0.0)
    font["post"].italicAngle = angle
    if angle:
        hhea.caretSlopeRise = 1000
        hhea.caretSlopeRun = round(1000 * math.tan(math.radians(-angle)))
    else:
        hhea.caretSlopeRise = 1
        hhea.caretSlopeRun = 0

    if "CFF " in font:
        cff_top = font["CFF "].cff[0]
        cff_top.ItalicAngle = angle
        cff_top.FamilyName = family
        cff_top.FullName = full_name
        cff_top.Weight = subfamily if subfamily != "Italic" else "Regular"

    font.save(path)
    print(f"{path}: {full_name!r} weight={style['weight']} "
          f"fsSelection={os2.fsSelection:#06x} macStyle={head.macStyle:#x} "
          f"italicAngle={angle}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    for p in sys.argv[1:]:
        process(p)
