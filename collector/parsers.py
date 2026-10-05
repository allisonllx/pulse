from __future__ import annotations
import hashlib, json, re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit, parse_qs, urlunsplit
from bs4 import BeautifulSoup
from .jobs import utcnow


def canonical_url(url):
    p = urlsplit(url.strip())
    if p.scheme not in ("http", "https") or not p.netloc or p.username or p.password:
        return None
    # Preserve query identity; only remove fragments. Never collapse names to URLs.
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))


def extract_json(html, marker="ytInitialData"):
    match = re.search(r"(?:var\s+)?"+marker+r"\s*=\s*",html)
    if not match:
        return {}
    try:
        return json.JSONDecoder().raw_decode(html[match.end():])[0]
    except ValueError:
        return {}


def parse(raw, job, observed_at=None):
    text = raw.decode("utf-8",errors="replace")
    candidates = []
    if job.surface == "local_rss":
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        for node in root.findall(".//item"):
            candidates.append((node.findtext("title", ""),node.findtext("link", ""),BeautifulSoup(node.findtext("description", ""),"html.parser").get_text(" ",strip=True)))
    elif job.source == "youtube":
        def walk(obj):
            if isinstance(obj,dict):
                video = obj.get("videoRenderer")
                if video and video.get("videoId"):
                    title = "".join(x.get("text","") for x in video.get("title",{}).get("runs",[])) or video.get("title",{}).get("simpleText","")
                    candidates.append((title,"https://www.youtube.com/watch?v="+video["videoId"],""))
                for v in obj.values():
                    walk(v)
            elif isinstance(obj,list):
                for v in obj: walk(v)
        walk(extract_json(text))
    else:
        soup = BeautifulSoup(text,"html.parser")
        if job.source == "google_news":
            for article in soup.select("article"):
                link = article.select_one("a[href].gPFEn") or article.select_one("h3 a[href],h4 a[href]") or next((a for a in article.select("a[href]") if a.get_text(strip=True)),None)
                if link:
                    candidates.append((link.get_text(" ",strip=True),urljoin(job.url,link["href"]),""))
        elif job.source == "google_search":
            for heading in soup.select("h3"):
                link = heading.find_parent("a",href=True)
                if not link: continue
                url = link["href"]
                if url.startswith("/url?"):
                    params = parse_qs(urlsplit(url).query)
                    url = params.get("q",params.get("url",[""]))[0]
                parent = heading.find_parent("div")
                candidates.append((heading.get_text(" ",strip=True),url,parent.get_text(" ",strip=True) if parent else ""))
        else:
            for link in soup.select("a[href*='/video/']"):
                candidates.append((link.get_text(" ",strip=True) or link.get("title", ""),urljoin(job.url,link["href"]),""))
    seen, items = set(), []
    for title,url,snippet in candidates:
        url = canonical_url(url)
        if not title.strip() or not url or url in seen: continue
        seen.add(url)
        items.append({"id":hashlib.sha256(url.encode()).hexdigest()[:24], "title":title.strip(), "url":url,
                      "rank":len(items)+1,"source":job.source,"surface":job.surface,"query":job.query,
                      "language":job.language,"snippet":snippet[:1200],"observationId":job.id,
                      "observedAt":observed_at or utcnow()})
        if len(items)>=20: break
    return items
