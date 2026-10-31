"""Merge two SVG cards side by side into one SVG."""
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET


def load(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"<\?xml[^>]*\?>", "", s).strip()
    tag = re.search(r"<svg\b[^>]*>", s)
    if not tag:
        raise ValueError(f"{path}: no <svg> root")
    vb = re.search(r"viewBox=([\"'])([^\"']+)\1", tag.group(0))
    if vb:
        w, h = map(float, vb.group(2).replace(",", " ").split()[2:4])
    else:
        dim = lambda a: float(re.search(a + r"=[\"']([\d.]+)", tag.group(0)).group(1))
        w, h = dim("width"), dim("height")
        # keep the card's internal coordinates when it has no viewBox
        s = s[: tag.end() - 1] + f' viewBox="0 0 {w:g} {h:g}">' + s[tag.end():]
        tag = re.search(r"<svg\b[^>]*>", s)
    return s, tag, w, h


def place(card, x, height):
    s, tag, w, h = card
    width = w * height / h
    # drop the card's own size/position, then set the new ones
    t = re.sub(r"\s(?:width|height|x|y)=([\"']).*?\1", "", tag.group(0))
    t = t[:-1] + f' x="{x:g}" y="0" width="{width:g}" height="{height:g}">'
    return s[: tag.start()] + t + s[tag.end():], width


def trophy_gap_ratio(path):
    """Gap between the first two trophies as a fraction of the image width."""
    root = ET.parse(path).getroot()
    width = float(root.get("viewBox").split()[2])
    boxes = sorted(
        (float(c.get("x")), float(c.get("width")))
        for c in root
        if c.tag.endswith("}svg") and c.get("x") is not None
    )
    (x1, w1), (x2, _) = boxes[:2]
    return (x2 - (x1 + w1)) / width


def main(left_path, right_path, out_path, gap="10"):
    left, right = load(left_path), load(right_path)
    height = left[3]
    if gap.endswith(".svg"):
        ratio = trophy_gap_ratio(gap)
        cards = left[2] * height / left[3] + right[2] * height / right[3]
        gap = ratio * cards / (1 - ratio)
    else:
        gap = float(gap)
    left_svg, lw = place(left, 0, height)
    right_svg, rw = place(right, lw + gap, height)
    total = lw + gap + rw

    out = (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{total:g}" height="{height:g}" viewBox="0 0 {total:g} {height:g}">\n'
        f"{left_svg}\n{right_svg}\n</svg>\n"
    )
    ET.fromstring(out)  # raises if the result is not well-formed

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(out_path) or ".", suffix=".svg")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, out_path)
    print(f"ok: {out_path} ({total:g} x {height:g})")


if __name__ == "__main__":
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    main(*sys.argv[1:])