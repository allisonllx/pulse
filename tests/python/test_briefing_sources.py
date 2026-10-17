from pathlib import Path
from collector.briefing.config import load_catalog
from collector.briefing.adapters.rss import parse_feed


RSS = b'''<rss><channel><item><title>AI model serving release</title><link>https://example.com/release?utm_source=rss</link><pubDate>Wed, 14 Oct 2026 12:00:00 GMT</pubDate><description>&lt;p&gt;New GPU support.&lt;/p&gt;</description></item><item><title>Undated</title><link>https://example.com/old</link></item></channel></rss>'''


def test_feed_dates_and_lens_assignment():
    result, rejected = parse_feed(RSS, {'id': 'example', 'publisherGroup': 'example'},
                                 '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert rejected == 1
    assert result[0].canonicalUrl == 'https://example.com/release'
    assert result[0].lensCandidates == ['all', 'tech']
    assert result[0].excerpt == 'New GPU support.'


def test_atom_supports_updated_only_without_claiming_publication():
    xml = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Update</title><link href="https://example.com/a"/><updated>2026-10-14T00:00:00Z</updated></entry></feed>'
    signals, rejected = parse_feed(xml, {'id': 'example'}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert signals == []
    assert rejected == 1


def test_discussion_links_point_to_thread_and_keep_article_as_context():
    xml = b'<rss><channel><item><title>GPU release discussion</title><link>https://example.com/article</link><comments>https://news.ycombinator.com/item?id=7</comments><pubDate>Wed, 14 Oct 2026 12:00:00 GMT</pubDate><description>Points: 42 # Comments: 5</description></item></channel></rss>'
    signals, _ = parse_feed(xml, {'id': 'hacker-news', 'evidenceKind': 'discussion'}, '2026-10-18T00:00:00Z', load_catalog(Path('config/briefing-lenses.json')))
    assert signals[0].canonicalUrl == 'https://news.ycombinator.com/item?id=7'
    assert signals[0].evidenceUrls == ['https://example.com/article']
    assert signals[0].metrics == {'points': 42, 'comments': 5}
    assert signals[0].excerpt == 'Public discussion on Hacker News: 42 points and 5 comments at collection.'


def test_same_story_across_feeds_keeps_independent_observation_ids():
    catalog = load_catalog(Path('config/briefing-lenses.json'))
    a, _ = parse_feed(RSS, {'id': 'feed-a'}, '2026-10-18T00:00:00Z', catalog)
    b, _ = parse_feed(RSS, {'id': 'feed-b'}, '2026-10-18T00:00:00Z', catalog)
    assert a[0].id != b[0].id
    assert a[0].canonicalUrl == b[0].canonicalUrl
