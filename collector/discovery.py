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

# Content-oriented phrases, paired by category rather than literal translation.
BROAD_CATEGORIES = ['sports','music','film_tv','gaming','culture','science_tech','public_affairs']
BROAD_PHRASES = {
 'en': [
  ['soccer match highlights goals','basketball game highlights NBA'],
  ['new music release official music video','live concert performance'],
  ['new movie official trailer','new TV series review episode'],
  ['new indie game release gameplay','new game update patch gameplay'],
  ['street food festival vlog','viral dance challenge original'],
  ['space mission launch footage','new gadget hands on review'],
  ['breaking news eyewitness report','election debate analysis'],
 ],
 'ja': [
  ['サッカー 試合 ハイライト ゴール','バスケットボール 試合 ハイライト NBA'],
  ['新曲 公式 ミュージックビデオ','ライブ コンサート パフォーマンス'],
  ['新作映画 公式予告編','新ドラマ 最新話 レビュー'],
  ['新作 インディーゲーム プレイ動画','ゲーム 最新アップデート 解説'],
  ['屋台 フードフェス vlog','話題 ダンス チャレンジ'],
  ['宇宙 ロケット 打ち上げ 映像','新製品 ガジェット 実機 レビュー'],
  ['速報 ニュース 現地取材','選挙 討論 分析'],
 ],
 'hi': [
  ['फुटबॉल मैच हाइलाइट्स गोल','बास्केटबॉल मैच हाइलाइट्स NBA'],
  ['नया गाना आधिकारिक म्यूजिक वीडियो','लाइव कॉन्सर्ट परफॉर्मेंस'],
  ['नई फिल्म आधिकारिक ट्रेलर','नई वेब सीरीज एपिसोड रिव्यू'],
  ['नया इंडी गेम गेमप्ले','गेम नया अपडेट पैच गेमप्ले'],
  ['स्ट्रीट फूड फेस्टिवल व्लॉग','वायरल डांस चैलेंज'],
  ['अंतरिक्ष मिशन रॉकेट लॉन्च वीडियो','नया गैजेट हैंड्स ऑन रिव्यू'],
  ['ताजा खबर घटनास्थल रिपोर्ट','चुनाव बहस विश्लेषण'],
 ],
 'pt': [
  ['melhores momentos futebol gols','melhores momentos basquete NBA'],
  ['lançamento música clipe oficial','show ao vivo apresentação'],
  ['novo filme trailer oficial','nova série crítica episódio'],
  ['lançamento jogo indie gameplay','nova atualização jogo gameplay'],
  ['festival comida de rua vlog','desafio dança viral original'],
  ['missão espacial lançamento foguete imagens','novo gadget teste análise'],
  ['notícias urgentes reportagem no local','eleição debate análise'],
 ],
 'fr': [
  ['résumé match football buts','résumé match basketball NBA'],
  ['nouvelle chanson clip officiel','concert performance live'],
  ['nouveau film bande annonce officielle','nouvelle série critique épisode'],
  ['nouveau jeu indépendant gameplay','nouvelle mise à jour jeu gameplay'],
  ['festival cuisine de rue vlog','défi danse viral original'],
  ['mission spatiale lancement fusée vidéo','nouveau gadget test prise en main'],
  ['actualité reportage sur place','élection débat analyse'],
 ],
 'de': [
  ['Fußball Spiel Highlights Tore','Basketball Spiel Highlights NBA'],
  ['neuer Song offizielles Musikvideo','Konzert Live Auftritt'],
  ['neuer Film offizieller Trailer','neue Serie Folge Kritik'],
  ['neues Indie Spiel Gameplay','neues Spiel Update Gameplay'],
  ['Streetfood Festival Vlog','viraler Tanz Challenge Original'],
  ['Weltraummission Raketenstart Aufnahmen','neues Gadget Hands on Test'],
  ['Eilmeldung Reportage vor Ort','Wahl Debatte Analyse'],
 ],
 'es': [
  ['resumen partido fútbol goles','resumen partido baloncesto NBA'],
  ['nueva canción video musical oficial','concierto actuación en vivo'],
  ['nueva película tráiler oficial','nueva serie reseña episodio'],
  ['nuevo juego indie gameplay','nueva actualización juego gameplay'],
  ['festival comida callejera vlog','reto baile viral original'],
  ['misión espacial lanzamiento cohete imágenes','nuevo dispositivo prueba primeras impresiones'],
  ['última hora reportaje en el lugar','elecciones debate análisis'],
 ],
}

def broad_queries(window, language='en', include_ai=True):
 if language not in BROAD_PHRASES:raise ValueError('Unsupported local discovery language')
 origin=int(datetime.fromisoformat('2026-10-05T06:00:00+00:00').timestamp())//21600
 slot=int(datetime.fromisoformat(window.replace('Z','+00:00')).timestamp())//21600-origin
 indices=[(slot*3+i)%len(BROAD_CATEGORIES) for i in range(3)]
 variant=(slot//len(BROAD_CATEGORIES))%2
 queries=[BROAD_PHRASES[language][i][variant] for i in indices]
 # Main English panel keeps two repeatable AI controls after the broad slots.
 return queries+ANCHORS if include_ai else queries

def query_category(query):
 if query in ANCHORS:return 'ai'
 if query=='football match highlights goals':return 'sports'  # Dated pilot wording.
 for phrases in BROAD_PHRASES.values():
  for category,variants in zip(BROAD_CATEGORIES,phrases):
   if query in variants:return category
 return None
