from __future__ import annotations
import hashlib, json, re, time, uuid
from urllib.parse import quote, urlsplit, urljoin
import httpx
from .jobs import utcnow
from .parsers import parse

LOCATION_URL = "https://ip.oxylabs.io/location"
HTTP_CAP = 2_000_000
LOCATION_CAP = 32_000
BROWSER_CAP = 5_000_000
MAX_ATTEMPTS = 3
# Conservative budget ceiling includes request and header overhead and three attempts.
JOB_RESERVATION = MAX_ATTEMPTS * (HTTP_CAP + 2 * LOCATION_CAP + 512_000)
BROWSER_RESERVATION = MAX_ATTEMPTS * (BROWSER_CAP + 2 * LOCATION_CAP + 512_000)

class FetchError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def redact(value, settings):
    text = str(value)
    for secret in (settings.username, settings.password, settings.proxy_host):
        if secret: text = text.replace(secret,"[redacted]")
    text = re.sub(r"https?://[^\s]+", "[url]", text)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[ip]", text)
    return text


def proxy_parts(settings,country,session):
    base = settings.username.removeprefix("customer-")
    username = "customer-"+base+"-cc-"+country.lower()+"-sessid-"+session
    server = "http://"+settings.proxy_host+":"+str(settings.proxy_port)
    url = "http://"+quote(username,safe="")+":"+quote(settings.password,safe="")+"@"+settings.proxy_host+":"+str(settings.proxy_port)
    return server,username,url


def location_country(raw):
    data = json.loads(raw)
    providers = data.get("providers",{})
    if providers:
        codes = {str(p.get("country") or p.get("country_code") or "").upper() for p in providers.values() if isinstance(p,dict)}-{ "" }
        # Reject disagreement rather than selecting the provider that matches our target.
        return next(iter(codes)) if len(codes)==1 else ""
    country = data.get("country") or data.get("country_code")
    if isinstance(country,dict): country = country.get("code") or country.get("iso_code")
    # Oxylabs location response also exposes country under geo.
    if not country and isinstance(data.get("geo"),dict):
        country = data["geo"].get("country") or data["geo"].get("country_code")
    return str(country or "").upper()


class HTTPAdapter:
    def __init__(self,settings,store,client_factory=None,sleep=time.sleep):
        self.settings,self.store = settings,store
        self.client_factory = client_factory or httpx.Client
        self.sleep = sleep

    def request(self,client,url,job,kind,cap):
        count = 0
        raw = bytearray()
        status = "transport_error"
        try:
            for hop in range(6):
                if urlsplit(url).scheme not in {"http","https"} or urlsplit(url).username or urlsplit(url).password:
                    raise FetchError("unsafe_redirect")
                count += len(url.encode()) + 1024
                raw = bytearray()
                with client.stream("GET",url,follow_redirects=False) as response:
                    count += sum(len(k)+len(v)+4 for k,v in response.headers.items())
                    status = "http_"+str(response.status_code)
                    wire = 0
                    for chunk in response.iter_bytes(chunk_size=16384):
                        raw.extend(chunk)
                        current_wire = response.num_bytes_downloaded
                        count += max(len(chunk),current_wire-wire)
                        wire = current_wire
                        if len(raw)>cap or count>cap: raise FetchError("response_too_large")
                    if response.status_code in {301,302,303,307,308}:
                        if kind=="request": self.store.account(job.id,"redirect_evidence",0,status,bytes(raw))
                        if hop>=5 or not response.headers.get("location"): raise FetchError("redirect_limit")
                        url = urljoin(url,response.headers["location"])
                        continue
                    response.raise_for_status()
                break
            status = "success"
            return bytes(raw)
        except FetchError: raise
        except httpx.HTTPStatusError as error:
            raise FetchError("http_"+str(error.response.status_code)) from None
        except Exception:
            # Proxy accounting can include bytes we never receive; conservatively charge cap.
            count = max(count,cap)
            raise FetchError("transport_error") from None
        finally:
            self.store.account(job.id,kind,count,status,bytes(raw) if kind=="request" else b"")

    def fetch_content(self,client,job,server,username):
        return self.request(client,job.url,job,"request",HTTP_CAP)

    def fetch(self,job):
        session = uuid.uuid4().hex
        server,username,proxy = proxy_parts(self.settings,job.country,session)
        result = {"status":"failed","observedCountry":None,"sessionRef":hashlib.sha256(session.encode()).hexdigest()[:16],"raw":b""}
        start = self.store.job_spent(job.id)
        for attempt in range(MAX_ATTEMPTS):
            try:
                with self.client_factory(proxy=proxy,timeout=30,follow_redirects=False,headers={"Accept-Language":job.language,"Accept-Encoding":"gzip","User-Agent":"Mozilla/5.0 WorldviewResearch/1.0"}) as client:
                    observed = location_country(self.request(client,LOCATION_URL,job,"location",LOCATION_CAP))
                    result["observedCountry"] = observed or None
                    if observed != job.country: raise FetchError("geography_mismatch")
                    raw = self.fetch_content(client,job,server,username)
                    result["raw"] = raw
                    # Verify again after retrieval using the identical sticky session.
                    after = location_country(self.request(client,LOCATION_URL,job,"location",LOCATION_CAP))
                    result["observedCountry"] = after or None
                    if after != job.country: raise FetchError("geography_changed")
                    result["raw"] = raw
                    result["observedAt"] = utcnow()
                    items = parse(raw,job,result["observedAt"])
                    if not items: raise FetchError("blocked_or_empty_extraction")
                    result["status"] = "success"
                    result["bytes"] = self.store.job_spent(job.id)-start
                    return result,items
            except FetchError as error:
                result["error"] = error.code
                if error.code in {"geography_mismatch","geography_changed","response_too_large","browser_unavailable"}: break
            except Exception:
                result["error"] = "adapter_error"  # Never stringify exceptions carrying proxy credentials.
            if attempt+1 < MAX_ATTEMPTS: self.sleep(min(2**attempt,4))
        result["bytes"] = self.store.job_spent(job.id)-start
        result.setdefault("observedAt",utcnow())
        return result,[]

class PlaywrightAdapter(HTTPAdapter):
    def fetch_content(self,client,job,server,username):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise FetchError("browser_unavailable") from None
        count,requests = [0],[0]
        raw = b""
        status = "browser_error"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True,proxy={"server":server,"username":username,"password":self.settings.password})
                context = browser.new_context(locale="en-US" if job.profile=="english" else job.language, extra_http_headers={"Accept-Language":job.language})
                page = context.new_page()
                cdp = context.new_cdp_session(page)
                cdp.send("Network.enable")
                def received(event):
                    count[0] += event.get("encodedDataLength",0)
                    if count[0]>BROWSER_CAP:
                        cdp.send("Page.stopLoading")
                cdp.on("Network.dataReceived",received)
                def route_request(route):
                    requests[0] += 1
                    count[0] += len(route.request.url.encode())+1024
                    host = urlsplit(route.request.url).hostname or ""
                    allowed = {"google_news":("google.com","gstatic.com"),"google_search":("google.com","gstatic.com"),"youtube":("youtube.com","googlevideo.com","ytimg.com","google.com"),"tiktok":("tiktok.com","tiktokcdn.com")}[job.source]
                    if count[0]>=BROWSER_CAP or requests[0]>40 or route.request.resource_type in {"image","media","font"} or not any(host==d or host.endswith("."+d) for d in allowed):
                        route.abort()
                    else: route.continue_()
                context.route("**/*",route_request)
                page.goto(job.url,wait_until="domcontentloaded",timeout=25000)
                page.wait_for_timeout(1500)
                raw = page.content().encode()
                if len(raw)>BROWSER_CAP:raise FetchError("response_too_large")
                browser.close()
                if count[0] > BROWSER_CAP: raise FetchError("response_too_large")
                status = "success"
                return raw
        except FetchError: raise
        except Exception:
            raise FetchError("browser_unavailable_or_blocked") from None
        finally:
            # Charge a full allocation on failed browser attempts (unknown in-flight bytes).
            self.store.account(job.id,"browser",count[0] if status=="success" else max(count[0],BROWSER_CAP),status,raw)
