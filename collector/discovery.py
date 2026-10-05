"""Bounded expanded search discovery; original controls remain separately labeled."""
from datetime import datetime
ANCHORS=['new AI agent demo','AI model release benchmark']
ROTATING=[
 'AI coding assistant new release demo',
 'site:x.com AI demo open source',
 'site:github.com AI agents releases',
 'open source multimodal model release',
 'AI research paper code implementation',
 'AI developer tool launch demo',
 'new music releases official music video',
 'new album release review',
 'new indie game release gameplay',
 'new game update patch gameplay',
]
def discovery_queries(window,source):
 # Same five slots in every country: two anchors and three rotating queries.
 # A ten-query rotation broadens coverage without multiplying request volume.
 slot=int(datetime.fromisoformat(window.replace('Z','+00:00')).timestamp())//21600
 start=(slot*3)%len(ROTATING)
 queries=ANCHORS+[ROTATING[(start+i)%len(ROTATING)] for i in range(3)]
 if source=='youtube':
  queries=[q.replace('site:x.com AI demo open source','new AI project demo open source').replace('site:github.com AI agents releases','open source AI agent GitHub release demo') for q in queries]
 return queries
