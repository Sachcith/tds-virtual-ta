import requests
import json
from dateutil.parser import parse
import time
from datetime import datetime

START = datetime.strptime('2025-01-01', "%Y-%m-%d").date()
END   = datetime.strptime('2025-04-14', "%Y-%m-%d").date()


BASE = "https://discourse.onlinedegree.iitm.ac.in"
CATEGORY_ID = 34
START, END = '2025-01-01', '2025-04-14'

# 👇 Your copied session cookie goes here
COOKIE = "_forum_session=BdoJ3JpGWecI7a0%2FxwZqvXqnIAGm58t0%2BjNzwNa24U7l2OzWuSlT%2BOz3Z22FG%2BjqnD2BGimvLlq%2B4B6qNafvEVzIsDACgpBsnN63OwYYm6B9CO3x6dLG%2FBamdQwGNm4zjiVY7uWu6NfRe5hX40XMhW7MG68HauAKPJ4A22EaPs8FBpQkqw79aKai%2FLBQ6dFxawYYC1UeJg4QN5D6%2BTVLH%2B9rZDeLfVsdGN6sXZ%2Be2qHc1qLZp48MdNSFJJonBIEiu93bjIlvSjBf%2Fy%2BvV10EaD7hm6s9uQ%3D%3D--ddtKZIZL%2F2jCXhea--mcw7RvmDP%2BOzYRe56F1%2FdQ%3D%3D; _t=qXoNcBs2uFcBftzcumzlW0%2FsoHyqxwfY2N7zHjuMi9uwrhGeJQ%2BOpQVoZOGPPgLF1eTGh8GObk3j3rZvZswX085eAho0SC6oaRHzm%2Fr8EMQ5xm%2B6zM9d9nrG9BjHTlyiFFgOc0l8yKxSo196fPJMzGhPpldgHiz8do99RcTaA71eWWmVN%2B7klVa4US3n%2FQWXGrgHpgeV4njUVHLFOJcxaq0SqV7yDQxUf5CcArZGINrNxflpzy4Sw%2FXpqBu3eMBnbflXubchs%2BvzlZFQGl9Vxc3OzBrMmkiu55Ily4XbaVmn%2FO%2FTIExmCfpJfFZro0uD--AOkRXlf%2BYaxgFEec--15DwMsFBplCLkRZ4lbQOEg%3D%3D;"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://discourse.onlinedegree.iitm.ac.in/",
    "Cookie": COOKIE
}

def fetch_topic_page(page):
    url = f"{BASE}/c/courses/tds-kb/{CATEGORY_ID}.json?page={page}"
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        return res.json().get("topic_list", {}).get("topics", [])
    except Exception as e:
        print(f"Error fetching page {page}: {e}")
        return []

def filter_topics(topics):
    filtered = []
    global START
    global END
    for t in topics:
        try:
            dt = parse(t['created_at']).date()
            if START <= str(dt) <= END:
                filtered.append({
                    'id': t['id'],
                    'title': t['title'],
                    'created_at': str(dt),
                    'url': f"{BASE}/t/{t['slug']}/{t['id']}"
                })
        except Exception:
            continue
    return filtered

def scrape_all():
    page, all_posts = 0, []
    while True:
        print(f"Fetching topic list page {page}")
        topics = fetch_topic_page(page)
        if not topics:
            break
        batch = filter_topics(topics)
        '''if not batch:
            break'''
        all_posts.extend(batch)
        page += 1
        time.sleep(1)  # polite delay
    return all_posts

if __name__ == "__main__":
    posts = scrape_all()
    with open("discourse_posts.json", "w") as f:
        json.dump(posts, f, indent=2)
    print(f"✅ Saved {len(posts)} posts to 'discourse_posts.json'")
