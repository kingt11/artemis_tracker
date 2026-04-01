import httpx
import traceback
from state import load_state, update_state
from embeds import create_news
from webhook import send_discord_message

async def poll_snapi():
    url = "https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=5&ordering=-published_at"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("[SNAPI] Fetching articles...")
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            state = load_state()
            last_id = state.get("last_snapi_article_id", 0)
            
            print(f"[SNAPI] Got {len(results)} articles, last_seen_id={last_id}")
            
            max_id = last_id
            new_count = 0
            for article in reversed(results): # Process oldest first
                article_id = article.get("id")
                if article_id > last_id:
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
                
        except Exception as e:
            print(f"[SNAPI] Error: {type(e).__name__}: {e}")
            traceback.print_exc()
