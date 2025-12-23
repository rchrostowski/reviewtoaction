import requests
import pandas as pd

def serpapi_search_place(api_key: str, query: str, location: str | None = None) -> list[dict]:
    params = {
        "api_key": api_key,
        "engine": "google_maps",
        "q": query,
        "hl": "en",
    }
    if location:
        params["location"] = location

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    results = data.get("local_results") or data.get("place_results") or []
    places = []
    for item in results[:10]:
        places.append({
            "title": item.get("title") or item.get("name") or "Unknown",
            "address": item.get("address") or item.get("formatted_address") or "",
            "rating": item.get("rating"),
            "reviews": item.get("reviews") or item.get("reviews_count"),
            "place_id": item.get("place_id") or item.get("data_id") or item.get("id"),
            "data_id": item.get("data_id"),
        })

    if not places and data.get("place_results"):
        pr = data["place_results"]
        places.append({
            "title": pr.get("title") or pr.get("name") or "Unknown",
            "address": pr.get("address") or "",
            "rating": pr.get("rating"),
            "reviews": pr.get("reviews"),
            "place_id": pr.get("place_id") or pr.get("data_id") or pr.get("id"),
            "data_id": pr.get("data_id"),
        })

    return places

def serpapi_fetch_reviews(api_key: str, place_id_or_data_id: str, limit: int = 200) -> pd.DataFrame:
    params = {
        "api_key": api_key,
        "engine": "google_maps_reviews",
        "place_id": place_id_or_data_id,
        "hl": "en",
    }

    r = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    reviews = data.get("reviews") or data.get("reviews_results") or []

    rows = []
    for rv in reviews[:limit]:
        text = rv.get("snippet") or rv.get("text") or rv.get("content") or ""
        if not text:
            continue
        rows.append({
            "review_text": text,
            "rating": rv.get("rating"),
            "date": rv.get("date") or rv.get("time") or None,
        })

    return pd.DataFrame(rows)

