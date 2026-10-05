from __future__ import annotations
import hashlib, json, re
import base64
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
    if job.surface in {"local_rss","control_rss","watch_rss"}:
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        for node in root.findall(".//item"):
            candidates.append((node.findtext("title", ""),node.findtext("link", ""),BeautifulSoup(node.findtext("description", ""),"html.parser").get_text(" ",strip=True)))
    elif job.source == "youtube":
        data=extract_json(text)
        if job.surface=='discovery_week_popular':
            selected=set()
            def filters(value):
                if isinstance(value,dict):
                    f=value.get('searchFilterRenderer',{})
                    if f.get('status')=='FILTER_STATUS_SELECTED':selected.add(f.get('label',{}).get('simpleText',''))
                    for child in value.values():filters(child)
                elif isinstance(value,list):
                    for child in value:filters(child)
            filters(data)
            if not {'This week','Popularity'}<=selected:return []
        def walk(obj,section=""):
            if isinstance(obj,dict):
                shelf=obj.get('shelfRenderer')
                if shelf:section=''.join(x.get('text','') for x in shelf.get('title',{}).get('runs',[])) or shelf.get('title',{}).get('simpleText','')
                video = obj.get("videoRenderer") or obj.get('gridVideoRenderer')
                if video and video.get("videoId"):
                    title = "".join(x.get("text","") for x in video.get("title",{}).get("runs",[])) or video.get("title",{}).get("simpleText","")
                    def label(field):
                        value=video.get(field,{})
                        return value.get('simpleText','') or ''.join(x.get('text','') for x in value.get('runs',[]))
                    details=[('Shelf: '+section+'; sampled page order') if section else '']
                    if label('publishedTimeText'):details.append('Uploaded: '+label('publishedTimeText'))
                    if label('viewCountText'):details.append('Platform-wide views: '+label('viewCountText'))
                    candidates.append((title,"https://www.youtube.com/watch?v="+video["videoId"],'; '.join(x for x in details if x)))
                for v in obj.values():
                    walk(v,section)
            elif isinstance(obj,list):
                for v in obj: walk(v,section)
        walk(data)
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
        elif job.source == 'bing':
            for result in soup.select('li.b_algo'):
                link=result.select_one('h2 a[href]')
                if link:
                    url=link['href']
                    if urlsplit(url).hostname in {'www.bing.com','bing.com'} and urlsplit(url).path=='/ck/a':
                        encoded=parse_qs(urlsplit(url).query).get('u',[''])[0]
                        if not encoded.startswith('a1'):continue
                        try:url=base64.urlsafe_b64decode(encoded[2:]+'='*((-len(encoded[2:]))%4)).decode('utf-8')
                        except (ValueError,UnicodeError):continue
                    candidates.append((link.get_text(' ',strip=True),url,result.get_text(' ',strip=True)))
        elif job.source == 'reddit':
            for post in soup.select('shreddit-post[post-title][permalink]'):
                candidates.append((post['post-title'],urljoin(job.url,post['permalink']),'Public popular feed; sampled page order'))
        elif job.source == 'instagram':
            for link in soup.select("a[href*='/p/'],a[href*='/reel/']"):
                candidates.append((link.get_text(' ',strip=True) or link.get('title',''),urljoin(job.url,link['href']),''))
        else:
            def tiktok_items(value):
                if isinstance(value,dict):
                    author=value.get('author',{})
                    author=author if isinstance(author,dict) else {}
                    handle=author.get('uniqueId') or author.get('unique_id')
                    video_id=value.get('id') or value.get('aweme_id')
                    caption=value.get('desc')
                    if handle and video_id and isinstance(caption,str):
                        candidates.append((caption,'https://www.tiktok.com/@'+str(handle)+'/video/'+str(video_id),''))
                    for v in value.values():tiktok_items(v)
                elif isinstance(value,list):
                    for v in value:tiktok_items(v)
            for script in soup.select('script#SIGI_STATE,script#__UNIVERSAL_DATA_FOR_REHYDRATION__,script#__NEXT_DATA__'):
                try:tiktok_items(json.loads(script.string or script.get_text()))
                except (ValueError,TypeError):pass
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
