from collector.discovery import discovery_queries,ANCHORS,ROTATING
from collector.jobs import plan
from datetime import datetime,timedelta,timezone
from urllib.parse import parse_qs,urlsplit

def test_rotation_broadens_catalog_without_increasing_five_slots():
    start=datetime(2026,10,5,tzinfo=timezone.utc)
    seen=set()
    for n in range(10):
        window=(start+timedelta(hours=6*n)).isoformat()
        queries=discovery_queries(window,'bing')
        assert len(queries)==len(set(queries))==5
        assert queries[:2]==ANCHORS
        assert queries==discovery_queries(window,'bing')
        seen.update(queries)
    assert seen==set(ANCHORS+ROTATING)

def test_youtube_discovery_preserves_profile_controls_and_explicit_date_filter():
    window='2026-10-05T06:00:00Z'
    a=plan(['SG'],['youtube'],window,query_set='discovery-v1')
    b=plan(['BR'],['youtube'],window,query_set='discovery-v1')
    assert [j.query for j in a]==[j.query for j in b]
    assert len(a)==5
    for j in a:
        params=parse_qs(urlsplit(j.url).query)
        assert params['hl']==['en'] and params['gl']==['US']
        assert params['sp']==['CAMSAggD']
        assert j.surface=='discovery_week_popular' and j.settings['uploadDateFilter']=='this_week'
        assert 'site:' not in j.query
    assert all(j.surface=='search_html' for j in plan(['SG'],['youtube'],window))

def test_fresh_popular_claim_requires_selected_filters_and_preserves_view_labels():
    import json
    from collector.parsers import parse
    job=plan(['SG'],['youtube'],'2026-10-05T06:00:00Z',query_set='discovery-v1')[0]
    video={'videoRenderer':{'videoId':'demo','title':{'simpleText':'Agent demo'},'publishedTimeText':{'simpleText':'2 days ago'},'viewCountText':{'simpleText':'123 views'}}}
    assert not parse(('var ytInitialData = '+json.dumps(video)+';').encode(),job)
    data={'contents':video,'filters':[{'searchFilterRenderer':{'label':{'simpleText':label},'status':'FILTER_STATUS_SELECTED'}} for label in ['This week','Popularity']]}
    items=parse(('var ytInitialData = '+json.dumps(data)+';').encode(),job)
    assert len(items)==1 and 'Uploaded: 2 days ago' in items[0]['snippet']
    assert 'Platform-wide views: 123 views' in items[0]['snippet']
