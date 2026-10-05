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

def test_bing_tracking_wrappers_share_destination_identity():
 import base64
 job=plan(['SG'],['bing'],W)[0]
 destination='https://example.com/music'
 encoded='a1'+base64.urlsafe_b64encode(destination.encode()).decode().rstrip('=')
 raw=('<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?tracking=first&amp;u='+encoded+'">Music</a></h2></li><li class="b_algo"><h2><a href="https://www.bing.com/ck/a?tracking=second&amp;u='+encoded+'">Music again</a></h2></li>').encode()
 items=parse(raw,job,W)
 assert len(items)==1 and items[0]['url']==destination
 assert job.settings['gl'] is None and 'setlang=en-US' in job.url

def test_reddit_challenge_is_not_a_post_and_real_posts_are_extracted():
 job=plan(['US'],['reddit'],W)[0]
 assert not parse(b'<form><input name="js_challenge"></form>',job,W)
 items=parse(b'<shreddit-post post-title="A real public post" permalink="/r/example/comments/abc/title/"></shreddit-post>',job,W)
 assert items[0]['url']=='https://www.reddit.com/r/example/comments/abc/title/'
 assert job.query is None and job.settings['gl'] is None
