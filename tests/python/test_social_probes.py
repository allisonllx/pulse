import json
from collector.jobs import plan,Job
from collector.parsers import parse
W='2026-10-05T00:00:00Z'
def test_tiktok_hydration_produces_evidence_without_dom_links():
 job=plan(['SG'],['tiktok'],W)[0]
 data={'__DEFAULT_SCOPE__':{'webapp.search':{'itemList':[{'id':'12345','desc':'Real public caption','author':{'uniqueId':'creator'}}]}}}
 raw=('<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'+json.dumps(data)+'</script>').encode()
 items=parse(raw,job,W)
 assert len(items)==1
 assert items[0]['title']=='Real public caption'
 assert items[0]['url']=='https://www.tiktok.com/@creator/video/12345'
def test_tiktok_bootstrap_not_mistaken_for_results():
 job=plan(['SG'],['tiktok'],W)[0]
 assert not parse(b'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">{"config":{"id":"123","desc":"bootstrap"}}</script>',job,W)
def test_instagram_probe_is_bounded_and_has_no_invented_region_setting():
 jobs=plan(['US','SG'],['instagram'],W)
 assert len(jobs)==1
 assert jobs[0].settings['gl'] is None
def test_control_rss_is_distinct_from_local_edition():
 job=Job('SG',W,'english','google_news','control_rss',None,'https://news.google.com/rss?hl=en&gl=US','en')
 items=parse(b'<rss><channel><item><title>Headline</title><link>https://example.com/a</link></item></channel></rss>',job,W)
 assert items[0]['surface']=='control_rss' and items[0]['language']=='en'

def test_youtube_gaming_grids_preserve_shelf_and_sample_order():
 job=plan(['JP'],['youtube'],W,profile='local',youtube_surface='gaming_discovery')[0]
 data={'shelfRenderer':{'title':{'simpleText':'Featured'},'content':{'gridVideoRenderer':{'videoId':'abc123','title':{'simpleText':'Gaming video'}}}}}
 items=parse(('var ytInitialData = '+json.dumps(data)+';').encode(),job,W)
 assert job.profile=='local' and job.language=='ja' and 'gl=JP' in job.url
 assert items[0]['snippet']=='Shelf: Featured; sampled page order'
 assert items[0]['rank']==1 and items[0]['surface']=='gaming_discovery'

def test_exact_watch_phrase_is_a_distinct_rss_surface():
 from collector.jobs import plan_watches
 jobs=plan_watches(['SG','JP'],['cornell 7'],W)
 assert len(jobs)==2 and all(j.surface=='watch_rss' and j.query=='cornell 7' for j in jobs)
 assert 'q=%22cornell+7%22' in jobs[0].url

def test_translation_refresh_failure_does_not_abort_collection(store,monkeypatch):
 import collector.translations as translation
 from collector.cli import refresh_translations
 monkeypatch.setattr(translation,'translate_publication',lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('model unavailable')))
 assert refresh_translations('public/data',store)=={'status':'unavailable','error':'ValueError'}
