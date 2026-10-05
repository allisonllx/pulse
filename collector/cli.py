from __future__ import annotations
import argparse, json, sys, time
from dataclasses import asdict, replace
from pathlib import Path
from .settings import Settings,PILOT,EXPANSION,CAPABILITIES
from .settings import QUERIES,EXTRACTION_VERSION
from .jobs import plan,plan_watches,window_at,utcnow
from .store import Store
from .adapters import HTTPAdapter,PlaywrightAdapter,JOB_RESERVATION,BROWSER_RESERVATION
from .publish import publish,build_recording
from .archive import export_archive,restore_archive

def allocation_for(job):
    if job.adapter=='auto':return JOB_RESERVATION+BROWSER_RESERVATION
    return BROWSER_RESERVATION if job.adapter=='playwright' else JOB_RESERVATION


def budget_status(store,settings):
    reserve = (settings.budget_bytes+4)//5
    available = max(0,settings.budget_bytes-reserve-store.spent)
    return {"budgetBytes":settings.budget_bytes,"reserveBytes":reserve,"spentBytes":store.spent,"remainingBytes":available,"accounting":"conservative transfer estimate; requests, response headers, location checks, browser traffic and failed attempts included"}


def collect(store,settings,jobs,dry_run=False,adapter_factory=None):
    if not dry_run:store.expire_before(window_at())
    states = {r["id"]:r["state"] for r in store.rows("jobs")}
    remaining = [j for j in jobs if states.get(j.id)!="done"]
    projection = sum(allocation_for(j) for j in remaining)
    report = {"window":jobs[0].window if jobs else window_at(),"jobCount":len(jobs),"pendingJobs":len(remaining),"projectedBytes":projection,"budget":budget_status(store,settings),"capabilities":CAPABILITIES}
    report["fitsBudget"] = projection<=report["budget"]["remainingBytes"]
    if dry_run:return report
    settings.require_live()
    if not report["fitsBudget"]:raise ValueError("Projected traffic exceeds available budget after 20% reserve; use --dry-run and narrow sources/countries.")
    store.schedule(jobs)
    success,failed = 0,0
    last_host = {}
    for job in remaining:
        from urllib.parse import urlsplit
        if settings.expired(): break
        if adapter_factory is None and job.window!=window_at():
            store.expire_before(window_at());break
        host = urlsplit(job.url).hostname
        delay = max(0,settings.host_delay_seconds-(time.monotonic()-last_host.get(host,0)))
        if delay:time.sleep(delay)
        allocation = allocation_for(job)
        if allocation>budget_status(store,settings)["remainingBytes"]:break
        reservation = store.claim_budget(job,allocation,settings.budget_bytes)
        if reservation is None:continue
        cls = PlaywrightAdapter if job.adapter=="playwright" else HTTPAdapter
        adapter = adapter_factory(settings,store) if adapter_factory else cls(settings,store)
        result,items = adapter.fetch(job)
        if job.adapter=='auto' and adapter_factory is None and result['status']!='success' and result.get('error') in {'blocked_or_empty_extraction','http_403','http_429'}:
            result,items = PlaywrightAdapter(settings,store).fetch(job)
        last_host[host] = time.monotonic()
        result["bytes"] = store.job_spent(job.id)
        result["bytes"] -= allocation
        store.save(job,result,items)
        store.settle_budget(reservation)
        success += result["status"]=="success"
        failed += result["status"]!="success"
        print(json.dumps({"observationId":job.id,"country":job.country,"source":job.source,"surface":job.surface,"query":job.query,"status":result["status"],"error":result.get("error"),"bytes":result["bytes"]}),file=sys.stderr)
    return {**report,"successful":success,"failed":failed,"budget":budget_status(store,settings)}


def refresh_translations(destination,store):
    try:
        from .translations import translate_publication
        return translate_publication(destination,store.root/'translations.sqlite')
    except Exception as error:
        # Optional analysis must never stop time-sensitive source harvesting.
        print('worldview: translation refresh unavailable ('+type(error).__name__+'); originals preserved, collection continues.',file=sys.stderr)
        return {'status':'unavailable','error':type(error).__name__}


def make_parser():
    parser = argparse.ArgumentParser(prog="worldview",description="Bounded, verified six-hour Worldview recordings")
    parser.add_argument("--data-dir",type=Path,help="Local evidence directory")
    sub = parser.add_subparsers(dest="command",required=True)
    sub.add_parser("init")
    for command in ("collect","run"):
        p = sub.add_parser(command)
        p.add_argument("--once",action="store_true",help="One six-hour window (collect always runs once)")
        p.add_argument("--dry-run",action="store_true")
        p.add_argument("--countries",default=",".join(PILOT))
        p.add_argument("--expand",action="store_true")
        p.add_argument("--sources",default="google_news,google_search,youtube")
        p.add_argument("--profile",choices=["all","local","english"],default="all")
        p.add_argument("--queries",choices=QUERIES,nargs='+',help="Subset of the five fixed control queries for bounded probes")
        p.add_argument("--retry-failed",action="store_true",help="Retry failed observations only within the current window; attempt evidence remains")
        p.add_argument("--adapter",choices=["auto","http","playwright"],default="auto",help="Override source adapter; browser installation is explicit")
        p.add_argument("--youtube-surface",choices=["search_html","gaming_discovery"],default="search_html")
        p.add_argument("--watchlist",type=Path,help="JSON list of tracked news phrases for the selected countries")
        p.add_argument("--news-surface",choices=["local_rss","local_html"],default="local_rss")
        p.add_argument("--windows",type=int,default=44,help="Bounded foreground run: default eleven days / 44 windows")
        p.add_argument("--panel",type=Path,help="JSON list of country/source panels collected in the same window")
        p.add_argument("--publish-output",type=Path,help="Atomically publish after each completed window")
        p.add_argument("--embeddings",action="store_true",help="Use installed multilingual model for published topics")
        p.add_argument("--translations",action="store_true",help="Translate published headlines locally after each publication; initial model download may be required")
    for command in ("summarize","publish"):
        p = sub.add_parser(command)
        p.add_argument("--corrections",type=Path,default=Path("config/topic-corrections.json"))
        p.add_argument("--embeddings",action="store_true",help="Explicit model loading; downloads may be required")
        if command=="publish":
            p.add_argument("--output",type=Path,default=Path("public/data"))
            p.add_argument("--translations",action="store_true",help="Cache local English translations alongside original evidence")
    p = sub.add_parser("export");p.add_argument("output",type=Path)
    p = sub.add_parser("restore");p.add_argument("archive",type=Path)
    sub.add_parser("status")
    sub.add_parser("reextract",help="Re-run extraction from saved raw evidence, without network traffic")
    return parser


def main(argv=None):
    parser = make_parser();args = parser.parse_args(argv)
    try:
        settings = Settings.load()
        if args.data_dir:settings.data_dir = args.data_dir
        if args.command=="restore":
            print(json.dumps(restore_archive(args.archive,settings.data_dir)));return 0
        store = Store(settings.data_dir)
        try:
            if args.command=="init":result = {"initialized":str(settings.data_dir),"capabilities":CAPABILITIES}
            elif args.command=="status":result = {"budget":budget_status(store,settings),"jobs":{state:sum(r["state"]==state for r in store.rows("jobs")) for state in ("pending","running","done")},"health":store.rows("health"),"observations":len(store.rows("observations")),"clusterMethod":dict((r["key"],r["value"]) for r in store.rows("meta")).get("cluster_method","not summarized")}
            elif args.command in ("collect","run"):
                countries = list(dict.fromkeys(c.strip().upper() for c in args.countries.split(",") if c.strip()))
                if args.expand:countries = list(dict.fromkeys(countries+EXPANSION))
                sources = list(dict.fromkeys(s.strip() for s in args.sources.split(",") if s.strip()))
                if args.windows<1 or args.windows>60:raise ValueError("--windows must be between 1 and 60")
                last_window = None
                iterations = 1 if args.command=="collect" or args.once or args.dry_run else args.windows
                for iteration in range(iterations):
                    while last_window==window_at():
                        if settings.expired():raise ValueError("Proxy collection has expired; existing recording preserved.")
                        time.sleep(30)
                    if args.panel:
                        panels=json.loads(args.panel.read_text())
                        if not isinstance(panels,list) or not panels:raise ValueError("Panel must be a nonempty JSON list")
                        jobs=[]
                        panel_adapters={}
                        for panel in panels:
                            panel_jobs=plan(panel['countries'],panel['sources'],profile=panel.get('profile','all'),news_surface=args.news_surface,youtube_surface=panel.get('youtubeSurface','search_html'),query_set=panel.get('querySet'))
                            if 'queries' in panel:
                                if not isinstance(panel['queries'],list) or any(q not in QUERIES for q in panel['queries']):raise ValueError('Invalid panel queries')
                                panel_jobs=[j for j in panel_jobs if j.query is None or j.query in panel['queries']]
                            if 'queryLimit' in panel:
                                if type(panel['queryLimit']) is not int or not 1<=panel['queryLimit']<=5:raise ValueError('Invalid query limit')
                                allowed=set(j.query for j in panel_jobs[:panel['queryLimit']])
                                panel_jobs=[j for j in panel_jobs if j.query in allowed]
                            if panel.get('adapter'):
                                if panel['adapter'] not in {'http','playwright','auto'}:raise ValueError('Invalid panel adapter')
                                panel_adapters.update({j.id:panel['adapter'] for j in panel_jobs})
                            jobs.extend(panel_jobs)
                        jobs=list({j.id:j for j in jobs}.values())
                    else:jobs = plan(countries,sources,profile=args.profile,news_surface=args.news_surface,youtube_surface=args.youtube_surface)
                    if args.watchlist:
                        jobs.extend(plan_watches(countries,json.loads(args.watchlist.read_text())))
                    if args.queries:jobs=[j for j in jobs if j.query is None or j.query in args.queries]
                    if args.adapter!="auto":jobs = [replace(j,adapter=args.adapter) for j in jobs]
                    else:jobs=[replace(j,adapter='auto') if j.adapter=='http' else j for j in jobs]
                    if args.panel:jobs=[replace(j,adapter=panel_adapters.get(j.id,j.adapter)) for j in jobs]
                    if args.retry_failed and not args.dry_run:
                        with store.db:
                            for j in jobs:
                                if store.db.execute("SELECT 1 FROM observations WHERE id=? AND status!='success'",(j.id,)).fetchone():
                                    store.db.execute("DELETE FROM items WHERE observation_id=?",(j.id,))
                                    store.db.execute("DELETE FROM observations WHERE id=?",(j.id,))
                                    store.db.execute("UPDATE jobs SET state='pending',lease=NULL WHERE id=?",(j.id,))
                    result = collect(store,settings,jobs,args.dry_run)
                    planned_windows = 1 if args.command=="collect" or args.once else args.windows
                    result["plannedWindows"] = planned_windows
                    result["projectedRunBytes"] = result["projectedBytes"]*planned_windows
                    result["runFitsBudget"] = result["projectedRunBytes"]<=result["budget"]["remainingBytes"]
                    if args.publish_output and not args.dry_run:
                        corrections_path=Path('config/topic-corrections.json')
                        corrections=json.loads(corrections_path.read_text()) if corrections_path.exists() else None
                        result['publication']=publish(store,args.publish_output,corrections,args.embeddings)
                        if args.translations:
                            result['translations']=refresh_translations(args.publish_output,store)
                    last_window = jobs[0].window if jobs else window_at()
                    if iteration+1<iterations:print(json.dumps(result),flush=True)
            elif args.command=='reextract':
                import gzip
                from .jobs import Job
                from .parsers import parse
                jobs={r['id']:Job(**json.loads(r['payload'])) for r in store.rows('jobs')}
                count=0
                with store.db:
                    for obs in store.rows('observations'):
                        if not obs['raw_path']:continue
                        recover=obs['status']!='success' and obs['error']=='blocked_or_empty_extraction' and obs['observed_country']==obs['country']
                        if obs['status']!='success' and not recover:continue
                        items=parse(gzip.decompress((store.root/obs['raw_path']).read_bytes()),jobs[obs['job_id']],obs['observed_at'])
                        if not items:
                            if recover:continue
                            if jobs[obs['job_id']].surface!='watch_rss':raise ValueError('Re-extraction failed; normalized data preserved.')
                        store.db.execute('DELETE FROM items WHERE observation_id=?',(obs['id'],))
                        for item in items:store.db.execute('INSERT INTO items VALUES(?,?,?)',(item['id'],obs['id'],json.dumps(item,ensure_ascii=False)))
                        store.db.execute('UPDATE observations SET extraction_version=?,settings=? WHERE id=?',(EXTRACTION_VERSION,json.dumps(jobs[obs['job_id']].settings),obs['id']))
                        if recover:store.db.execute("UPDATE observations SET status='success',error='recovered_extraction_v3' WHERE id=?",(obs['id'],))
                        count+=1
                result={'reextracted':count,'extractorVersion':EXTRACTION_VERSION}
            elif args.command in ("summarize","publish"):
                corrections = json.loads(args.corrections.read_text()) if args.corrections.exists() else None
                if args.command=="publish":
                    result = publish(store,args.output,corrections,args.embeddings)
                    if args.translations:
                        result['translations']=refresh_translations(args.output,store)
                else:
                    recording = build_recording(store,corrections,args.embeddings)
                    result = {"snapshots":len(recording["snapshots"]),"topics":sum(len(s["topics"]) for s in recording["snapshots"]),"clusterVersion":recording["clusterVersion"],"clusterMethod":store.db.execute("SELECT value FROM meta WHERE key='cluster_method'").fetchone()[0]}
            else:result = export_archive(store,args.output)
            print(json.dumps(result,ensure_ascii=False,indent=2))
        finally:store.close()
        return 0
    except KeyboardInterrupt:
        print("Stopped; claimed jobs recover after their five-minute lease.",file=sys.stderr);return 130
    except Exception as error:
        # Exceptions are not exposed: HTTP/proxy library errors can include credentials.
        if isinstance(error,ValueError):print("worldview: "+str(error),file=sys.stderr)
        else:print("worldview: operation failed ("+type(error).__name__+"); local evidence preserved.",file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
