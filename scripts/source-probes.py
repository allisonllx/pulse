"""Bounded alternative surface probes. Run with the collector Python environment."""
from dataclasses import replace
from urllib.parse import urlencode
from collector.settings import Settings,COUNTRIES
from collector.store import Store
from collector.jobs import Job,window_at
from collector.cli import collect
import json
settings=Settings.load();store=Store(settings.data_dir)
try:
    jobs=[]
    for country in ['SG','US','JP']:
        lang=COUNTRIES[country][2]
        jobs.append(Job(country,window_at(),'local','youtube','gaming_discovery',None,'https://www.youtube.com/gaming?'+urlencode({'hl':lang,'gl':country}),lang,'http'))
    for country in ['SG','US']:
        jobs.append(Job(country,window_at(),'english','google_news','control_rss',None,'https://news.google.com/rss?hl=en&gl=US&ceid=US:en','en','http'))
    jobs.append(Job('US',window_at(),'english','instagram','public_keyword_probe','AI agents','https://www.instagram.com/explore/search/keyword/?q=AI%20agents','en','http'))
    print(json.dumps(collect(store,settings,jobs),indent=2))
finally:store.close()
