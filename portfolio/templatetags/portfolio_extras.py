"""Template filters for the portfolio app.

`richtext` is the important one: admin content is authored in Summernote and
much of it was pasted from Word / Notion, so it carries hardcoded
`font-family: Helvetica; font-size: 11pt; color: #000` inline styles, Word
namespace tags and `data-path-to-node` attributes. Those override the site's
typography and break dark mode (hardcoded black text on a black background).

Rather than rewriting the stored HTML — the source of truth stays in the DB —
we normalise it at render time.
"""

import re
from html.parser import HTMLParser
from html import escape

from django import template
from django.utils.safestring import mark_safe
from django_bleach.templatetags.bleach_tags import bleach_value

register = template.Library()


# --- richtext -------------------------------------------------------------

VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "col", "wbr"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
BLOCK_TAGS = {"p", "div", "ul", "ol", "li", "table", "blockquote", "pre", "hr"}

# Inline style properties that must not survive: they hardcode typography and
# colour, which fights the design tokens and the dark theme.
DROP_STYLE_PROPS = {
    "font-family", "font-size", "letter-spacing", "line-height",
    "color", "background", "background-color", "margin", "margin-top",
    "margin-bottom", "margin-left", "margin-right", "padding", "width",
    "height", "font-variant", "mso-fareast-font-family",
}
KEEP_STYLE_PROPS = {"font-weight", "text-align", "text-decoration", "font-style"}

DROP_ATTRS = {"data-path-to-node", "data-index-in-node", "lang", "align", "border",
              "cellpadding", "cellspacing", "bgcolor", "face", "size"}

# A pasted `font-size` at or above this many CSS px was acting as a subheading.
SUBHEAD_PX = 17.0


def _style_to_px(value):
    m = re.match(r"\s*([\d.]+)\s*(px|pt|em|rem)?\s*$", value or "")
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2) or "px"
    return {"px": num, "pt": num * 4 / 3, "em": num * 16, "rem": num * 16}[unit]


class _RichTextCleaner(HTMLParser):
    """Normalise admin-authored HTML into structural markup the stylesheet owns."""

    def __init__(self, heading_map=None):
        super().__init__(convert_charrefs=True)
        self.heading_map = heading_map or {}
        self.out = []
        self.stack = []          # currently open (rendered) tags
        self.list_depth = 0      # inside a real <ul>/<ol>?
        self.auto_ul = False     # we opened a <ul> to adopt orphan <li>s

    # -- helpers --
    def _emit(self, s):
        self.out.append(s)

    def _clean_attrs(self, tag, attrs):
        kept = []
        is_subhead = False
        classes = []
        for name, value in attrs:
            name = (name or "").lower()
            if name in DROP_ATTRS or name.startswith("data-") or name.startswith("mso"):
                continue
            if name == "style":
                style, is_subhead = self._clean_style(value)
                if style:
                    kept.append(("style", style))
                continue
            if name == "class":
                # Word emits class="0", "MsoNormal" etc. — drop those.
                for c in (value or "").split():
                    if not c.isdigit() and not c.lower().startswith("mso"):
                        classes.append(c)
                continue
            if name == "href" and value and value.strip().lower().startswith("javascript:"):
                continue
            kept.append((name, value))

        if is_subhead:
            classes.append("rt-lead")
        if classes:
            kept.append(("class", " ".join(dict.fromkeys(classes))))

        # External links open safely.
        href = dict(kept).get("href", "")
        if tag == "a" and href.startswith("http"):
            kept = [kv for kv in kept if kv[0] not in ("target", "rel")]
            kept += [("target", "_blank"), ("rel", "noopener noreferrer")]
        return kept, is_subhead

    def _clean_style(self, raw):
        keep = []
        subhead = False
        for decl in (raw or "").split(";"):
            if ":" not in decl:
                continue
            prop, _, val = decl.partition(":")
            prop = prop.strip().lower()
            val = val.strip()
            if prop == "font-size":
                px = _style_to_px(val)
                if px is not None and px >= SUBHEAD_PX:
                    subhead = True
                continue
            if prop in DROP_STYLE_PROPS or prop not in KEEP_STYLE_PROPS:
                continue
            if prop == "font-weight" and val in ("normal", "400"):
                continue
            keep.append(f"{prop}: {val}")
        return "; ".join(keep), subhead

    def _open_auto_ul(self):
        if self.list_depth == 0 and not self.auto_ul:
            self._emit("<ul>")
            self.auto_ul = True

    def _close_auto_ul(self):
        # Never break out of an <li> we are still inside.
        if self.auto_ul and "li" not in self.stack:
            self._emit("</ul>")
            self.auto_ul = False

    # -- parser callbacks --
    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        # Word / Office namespace junk.
        if ":" in tag or tag in ("o:p", "font", "meta", "link", "style", "script"):
            return

        # The section heading around this content is an <h2>, so remap the
        # author's arbitrary levels onto a gap-free h3/h4/h5 run.
        if tag in HEADINGS:
            tag = self.heading_map.get(tag, "h3")

        if tag == "li":
            self._open_auto_ul()
        elif tag not in ("ul", "ol") and self.auto_ul and tag in BLOCK_TAGS:
            self._close_auto_ul()

        attrs, is_subhead = self._clean_attrs(tag, attrs)

        # An empty <span> carries nothing once styles are stripped.
        if tag == "span" and not attrs:
            self.stack.append(None)
            return

        if tag == "span" and is_subhead:
            tag = "strong"

        if tag in ("ul", "ol"):
            self._close_auto_ul()
            self.list_depth += 1

        attr_str = "".join(
            f' {k}="{escape(str(v), quote=True)}"' for k, v in attrs if v is not None
        )
        self._emit(f"<{tag}{attr_str}>")
        if tag in VOID_TAGS:
            return
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if ":" in tag or tag in ("o:p", "font"):
            return
        if tag in VOID_TAGS:
            attrs, _ = self._clean_attrs(tag, attrs)
            attr_str = "".join(
                f' {k}="{escape(str(v), quote=True)}"' for k, v in attrs if v is not None
            )
            self._emit(f"<{tag}{attr_str}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if ":" in tag or tag in ("o:p", "font", "meta", "link", "style", "script"):
            return
        if tag in VOID_TAGS:
            return
        if not self.stack:
            return
        opened = self.stack.pop()
        if opened is None:          # dropped <span>
            return
        if opened in ("ul", "ol"):
            self.list_depth = max(0, self.list_depth - 1)
        self._emit(f"</{opened}>")

    def handle_data(self, data):
        self._emit(escape(data, quote=False))

    def handle_comment(self, data):
        return  # Word conditional comments

    def handle_entityref(self, name):
        self._emit(f"&{name};")

    def handle_charref(self, name):
        self._emit(f"&#{name};")

    def close(self):
        super().close()
        # Close anything the source left open.
        while self.stack:
            opened = self.stack.pop()
            if opened:
                self._emit(f"</{opened}>")
        self._close_auto_ul()

    def result(self):
        html = "".join(self.out)
        html = re.sub(r"<p>(\s|&nbsp;|<br\s*/?>)*</p>", "", html)   # empty paragraphs
        html = re.sub(r"(?:\s*<br\s*/?>\s*){3,}", "<br><br>", html)  # <br> spam
        return html


_HEADING_BLOCK_RE = re.compile(
    r"<h([1-6])\b([^>]*)>(.*?)</h\1\s*>", re.I | re.S
)


def _demote_wrapper_headings(html):
    """A heading that wraps block content is a wrapper, not a heading.

    Some records store an entire report inside a single `<h4>`, which makes
    every paragraph render at heading size and weight.
    """
    def sub(m):
        inner = m.group(3)
        if re.search(r"<\s*(p|ul|ol|li|table|div|hr)\b", inner, re.I):
            return f"<div{m.group(2)}>{inner}</div>"
        return m.group(0)

    return _HEADING_BLOCK_RE.sub(sub, html)


def _build_heading_map(html):
    """Compress whatever heading levels the author used into h3, h4, h5…

    Records vary: one uses only `<h4>`, another `<h2>` + `<h4>`. Mapping by
    rank rather than by absolute level keeps the outline gap-free under the
    page's `<h2>` section title.
    """
    used = sorted({int(m) for m in re.findall(r"<h([1-6])\b", html, re.I)})
    return {f"h{level}": f"h{min(3 + rank, 6)}" for rank, level in enumerate(used)}


@register.filter(is_safe=True)
def richtext(value):
    """Sanitise, then normalise, admin-authored HTML for display."""
    if not value:
        return ""
    cleaned = bleach_value(value)          # security policy from settings.BLEACH_*
    cleaned = _demote_wrapper_headings(str(cleaned))
    parser = _RichTextCleaner(heading_map=_build_heading_map(cleaned))
    parser.feed(cleaned)
    parser.close()
    return mark_safe(parser.result())      # noqa: S308 — bleach ran first


# --- plain-text helpers ---------------------------------------------------

@register.filter(is_safe=True)
def emphasise(value):
    """Render leftover markdown `**bold**` from plain-text fields.

    Several `outcome` fields were written in Notion and still carry literal
    asterisks. Escape first, then promote — never trust the raw value.
    """
    if not value:
        return ""
    out = escape(str(value))
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out, flags=re.S)
    return mark_safe(out)  # noqa: S308 — escaped above


@register.filter
def first_line(value):
    """The opening line of a multi-line field, used as a one-line summary.

    Several `description` values start with a written summary line and then
    continue into detail; joining them into one blob reads as a run-on.
    """
    if not value:
        return ""
    for line in str(value).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = line.strip()
        if line:
            return line
    return ""


#: 이보다 긴 요약은 카드에서 첫 문장만 씁니다. 상세 페이지에는 전문이 남습니다.
LEAD_MAX_CHARS = 120


@register.filter
def lead_text(value):
    """카드/대표 프로젝트에 쓸 한 줄 요약.

    설명 길이가 프로젝트마다 크게 달라 카드 높이가 들쭉날쭉해집니다.
    첫 줄을 쓰되, 그마저 길면 첫 문장에서 끊습니다.
    """
    text = first_line(value)
    if len(text) <= LEAD_MAX_CHARS:
        return text
    # 소수점(0.51308)에서 끊기지 않도록 마침표 뒤 공백을 경계로 씁니다.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if sentences and len(sentences[0]) >= 20:
        return sentences[0]
    return text[:LEAD_MAX_CHARS].rstrip() + "…"


@register.filter
def bullets(value):
    """Split a textarea written as `- item` lines into a list.

    Falls back to blank-line-separated paragraphs when there are no dashes.
    """
    if not value:
        return []
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in text.split("\n")]
    dashed = [ln.lstrip("-•·").strip() for ln in lines if ln.startswith(("-", "•", "·"))]
    if dashed:
        return [d for d in dashed if d]
    return [blk.strip() for blk in re.split(r"\n\s*\n", text) if blk.strip()]
