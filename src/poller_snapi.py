import httpx
from state import load_state, update_state
from embeds import create_news
from webhook import send_discord_message

async def poll_snapi():
    url = "https://api.spaceflightnewsapi.net/v4/articles/?search=Artemis+II&limit=5&ordering=-published_at"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            state = load_state()
            last_id = state.get("last_snapi_article_id", 0)
            
            max_id = last_id
            for article in reversed(results): # Process oldest first
                article_id = article.get("id")
                if article_id > last_id:
                    embed = create_news(
                        title=article.get("title"),
                        site=article.get("news_site"),
                        summary=article.get("summary"),
                        url=article.get("url"),
                        image_url=article.get("image_url")
                    )
                    await send_discord_message("NEWS", embed)
                    max_id = max(max_id, article_id)
                    
            if max_id > last_id:
                update_state("last_snapi_article_id", max_id)
                
        except Exception as e:
            print(f"Error fetching SNAPI data: {e}")
