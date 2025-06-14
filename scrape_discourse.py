import requests
import json
from bs4 import BeautifulSoup
from dateutil.parser import parse
import time

BASE = 'https://discourse.onlinedegree.iitm.ac.in'
START, END = '2025-01-01', '2025-04-14'

def fetch_posts(page=1):
    url = f"{BASE}/latest.json?page={page}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        return data.get('topic_list', {}).get('topics', [])
    except Exception as e:
        print(f"Error on page {page}: {e}")
        return []

def filter_by_date(topics):
    filtered = []
    for t in topics:
        try:
            dt = parse(t['created_at']).date()
            if START <= str(dt) <= END:
                filtered.append({'id': t['id'], 'title': t['title'], 'created_at': str(dt)})
        except:
            continue
    return filtered

def scrape_all():
    page, all_posts = 1, []
    while True:
        print(f"Fetching page {page}")
        topics = fetch_posts(page)
        if not topics:
            break
        batch = filter_by_date(topics)
        if not batch:
            break
        all_posts.extend(batch)
        page += 1
        time.sleep(1)  # polite delay
    return all_posts

if __name__ == '__main__':
    posts = scrape_all()
    with open('discourse_posts.json', 'w') as f:
        json.dump(posts, f, indent=2)
    print(f"Saved {len(posts)} posts.")
