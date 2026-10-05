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


def test_broad_category_rotation_and_local_profile_settings():
    from collector.discovery import broad_queries,BROAD_PHRASES,query_category
    start=datetime(2026,10,5,6,tzinfo=timezone.utc)
    seen=set()
    for n in range(14):
        window=(start+timedelta(hours=6*n)).isoformat()
        eng=broad_queries(window)
        local=broad_queries(window,'ja',False)
        assert len(eng)==5 and len(local)==3
        assert len({query_category(q) for q in eng[:3]})==3
        assert [query_category(q) for q in eng[:3]]==[query_category(q) for q in local]
        seen.update(eng[:3])
    assert seen=={q for pair in BROAD_PHRASES['en'] for q in pair}
    jobs=plan(['JP'],['youtube'],start.isoformat(),profile='local',query_set='broad-v2')
    assert len(jobs)==3
    assert all(j.profile=='local' and j.language=='ja' for j in jobs)
    assert all(j.settings['gl']=='JP' and j.settings['hl']=='en' and j.settings['querySet']=='broad-v2' for j in jobs)
    assert all(parse_qs(urlsplit(j.url).query)['sp']==['CAMSAggD'] for j in jobs)


def test_query_navigation_fallback_does_not_override_detected_topic_category():
    from collector.publish import topic_category
    assert topic_category('A match result', [{'discoveryCategory':'sports'}])=='sports'
    assert topic_category('AI agent release', [{'discoveryCategory':'sports'}])=='ai'
    assert topic_category('An unknown title', [])=='other'


def test_verified_local_filter_labels_are_checked_not_assumed():
    import json
    from collector.parsers import parse
    j=plan(['JP'],['youtube'],'2026-10-05T06:00:00Z',profile='local',query_set='broad-v2')[0]
    video={'videoRenderer':{'videoId':'soccer','title':{'simpleText':'試合ハイライト'}}}
    for labels in [('今週','人気度'),('Esta semana','Popularidade')]:
        data={'contents':video,'filters':[{'searchFilterRenderer':{'label':{'simpleText':label},'status':'FILTER_STATUS_SELECTED'}} for label in labels]}
        items=parse(('var ytInitialData = '+json.dumps(data)+';').encode(),j)
        assert items[0]['discoveryCategory']=='sports'
    data={'contents':video,'filters':[{'searchFilterRenderer':{'label':{'simpleText':'今週'},'status':'FILTER_STATUS_SELECTED'}}]}
    assert not parse(('var ytInitialData = '+json.dumps(data)+';').encode(),j)
