import httpx
import traceback
from state import load_state, update_state
from embeds import create_news
from webhook import send_discord_message

# Multiple search terms to catch all Artemis II coverage
SNAPI_SEARCHES = [
    "https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=10&ordering=-published_at",
    "https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+2&limit=10&ordering=-published_at",
    "https://api.spaceflightnewsapi.net/v4/articles/?search=SLS+Orion&limit=5&ordering=-published_at",
]

async def poll_snapi():
    async with httpx.AsyncClient(timeout=30.0) as client:
        state = load_state()
        last_id = state.get("last_snapi_article_id", 0)
        
        # Collect unique articles from all searches
        all_articles = {}
        for url in SNAPI_SEARCHES:
            try:
                print(f"[SNAPI] Fetching {url.split('search=')[1].split('&')[0]}...")
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                for article in data.get("results", []):
                    aid = article.get("id")
                    if aid and aid not in all_articles:
                        all_articles[aid] = article
            except Exception as e:
                print(f"[SNAPI] Error on query: {type(e).__name__}: {e}")
        
        print(f"[SNAPI] Got {len(all_articles)} unique articles, last_seen_id={last_id}")
        
        # Process new articles oldest-first
        new_articles = {aid: a for aid, a in all_articles.items() if aid > last_id}
        max_id = last_id
        new_count = 0
        
        for article_id in sorted(new_articles.keys()):
            article = new_articles[article_id]
            print(f"[SNAPI] New article: id={article_id}, title={article.get('title')}")
            embed = create_news(
                title=article.get("title"),
                site=article.get("news_site"),
                summary=article.get("summary"),
                url=article.get("url"),
                image_url=article.get("image_url")
            )
            await send_discord_message("NEWS", embed)
            max_id = max(max_id, article_id)
            new_count += 1
                
        if max_id > last_id:
            update_state("last_snapi_article_id", max_id)
        
        print(f"[SNAPI] Done. {new_count} new articles posted.")
