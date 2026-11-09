"""논문 메타데이터(제목·저자·학회·연도) 조회와 Google Drive 링크 해석.

표준 라이브러리만 사용합니다(새 의존성 없음).
  - arXiv  → arXiv API (journal_ref 가 있으면 학회/저널로 사용)
  - DOI    → Crossref API
  - 그 외  → 페이지의 citation_* <meta> 태그 (ACL Anthology, OpenReview, CVF,
             NeurIPS, ACM, IEEE, Springer 등 대부분의 논문 사이트가 제공)
"""
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

TIMEOUT = 10
MAX_BYTES = 1_000_000   # 논문 페이지 HTML 읽기 상한
# 연락처(이메일)를 넣지 않은 일반 UA. Crossref polite pool 은 쓰지 않습니다.
HEADERS = {"User-Agent": "about-me-portfolio/1.0"}

ARXIV_RE = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|^arxiv:\s*)"
    r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Za-z]{2})?/\d{7})(?:v\d+)?",
    re.IGNORECASE,
)
DOI_RE = re.compile(r"(10\.\d{4,9}/[^\s?#]+)")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


class MetaError(Exception):
    """메타데이터를 가져오지 못했을 때."""


def _get(url, limit=MAX_BYTES):
    if urlparse(url).scheme not in ("http", "https"):
        raise MetaError("http(s) 주소만 지원합니다.")
    try:
        with urlopen(Request(url, headers=HEADERS), timeout=TIMEOUT) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read(limit).decode(charset, errors="replace")
    except Exception as exc:   # noqa: BLE001 — 네트워크/HTTP/인코딩 오류를 한 종류로 통일
        raise MetaError(f"요청 실패 ({exc})") from exc


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _year(text):
    m = YEAR_RE.search(text or "")
    return int(m.group(0)) if m else None


def _from_arxiv(arxiv_id):
    # ponytail: stdlib ElementTree. 고정 호스트(export.arxiv.org, HTTPS) 응답만 파싱하고
    # 외부 엔티티는 기본 비활성이라 허용. 임의 호스트 XML 을 받게 되면 defusedxml 로 교체.
    ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
    try:
        entry = ET.fromstring(_get(f"https://export.arxiv.org/api/query?id_list={quote(arxiv_id)}")).find("a:entry", ns)
    except ET.ParseError as exc:
        raise MetaError("arXiv 응답을 해석하지 못했습니다.") from exc
    if entry is None or entry.find("a:title", ns) is None:
        raise MetaError("arXiv 에서 해당 논문을 찾지 못했습니다.")
    ref = _clean(entry.findtext("x:journal_ref", default="", namespaces=ns))
    return {
        "title": _clean(entry.findtext("a:title", namespaces=ns)),
        "authors": ", ".join(_clean(a.findtext("a:name", namespaces=ns)) for a in entry.findall("a:author", ns)),
        "venue": ref or "arXiv",
        "year": _year(ref) or _year(entry.findtext("a:published", namespaces=ns)),
    }


def _from_doi(doi):
    try:
        msg = json.loads(_get(f"https://api.crossref.org/works/{quote(doi)}"))["message"]
    except (ValueError, KeyError) as exc:
        raise MetaError("Crossref 응답을 해석하지 못했습니다.") from exc
    authors = ", ".join(_clean(f"{a.get('given', '')} {a.get('family', a.get('name', ''))}") for a in msg.get("author", []))
    parts = (msg.get("issued") or {}).get("date-parts") or [[None]]
    return {
        "title": _clean((msg.get("title") or [""])[0]),
        "authors": authors,
        "venue": _clean((msg.get("container-title") or [""])[0] or (msg.get("event") or {}).get("name", "")),
        "year": parts[0][0],
    }


class _CitationMeta(HTMLParser):
    """<meta name="citation_*"> 를 수집합니다(같은 이름이 여러 번 나올 수 있음 — 저자)."""

    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            name = (d.get("name") or "").lower()
            if name.startswith("citation_") and d.get("content"):
                self.meta.setdefault(name, []).append(d["content"])


def _from_page(url):
    parser = _CitationMeta()
    parser.feed(_get(url))
    m = parser.meta
    if "citation_title" not in m:
        raise MetaError("이 페이지에서 논문 정보(citation 메타태그)를 찾지 못했습니다.")
    first = lambda *keys: next((m[k][0] for k in keys if k in m), "")   # noqa: E731
    return {
        "title": _clean(m["citation_title"][0]),
        "authors": ", ".join(_clean(a) for a in m.get("citation_author", [])),
        "venue": _clean(first("citation_conference_title", "citation_journal_title", "citation_publisher")),
        "year": _year(first("citation_publication_date", "citation_date", "citation_online_date")),
    }


def fetch_metadata(source):
    """arXiv / DOI / 논문 페이지 주소로부터 {title, authors, venue, year} 를 반환합니다.

    Raises:
        MetaError: 조회 실패(네트워크, 미지원 형식, 논문 정보 없음).
    """
    source = (source or "").strip()
    if m := ARXIV_RE.search(source):
        return _from_arxiv(m.group(1))
    if m := DOI_RE.search(source):
        return _from_doi(m.group(1))
    return _from_page(source)


# ── Google Drive ─────────────────────────────────────────────

_DRIVE_FILE = re.compile(r"drive\.google\.com/(?:file/d/|open\?(?:[^#]*&)?id=|uc\?(?:[^#]*&)?id=)([\w-]+)")
_SLIDES = re.compile(r"docs\.google\.com/presentation/d/([\w-]+)")


def drive_links(url):
    """Drive 파일 / Google Slides 공유 링크에서 임베드·다운로드 주소를 만듭니다.

    Returns:
        dict | None: {"embed": ..., "download": ...}. Drive 링크가 아니면 None.

    Note:
        '링크가 있는 모든 사용자'로 공유된 파일만 비로그인 방문자에게 보입니다.
        비공개 파일 접근/폴더 자동 동기화는 Drive API(OAuth)가 필요해 지원하지 않습니다.
    """
    url = url or ""
    if m := _DRIVE_FILE.search(url):
        fid = m.group(1)
        return {
            "embed": f"https://drive.google.com/file/d/{fid}/preview",
            "download": f"https://drive.google.com/uc?export=download&id={fid}",
        }
    if m := _SLIDES.search(url):
        fid = m.group(1)
        return {
            "embed": f"https://docs.google.com/presentation/d/{fid}/embed",
            "download": f"https://docs.google.com/presentation/d/{fid}/export/pdf",
        }
    return None
