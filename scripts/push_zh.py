#!/usr/bin/env python3
"""
Push zh-TW content to tagsjapan.com/zh via REST API.
Run this ON the production server for best speed (localhost API calls).

Usage:
  python3 push_zh.py              # Push all 580 articles
  python3 push_zh.py --start=0 --end=10  # First 10 only

Config:
  - Edit WP_USER and WP_APP_PASS below
  - Edit BASE_URL if running locally (change to localhost URL)
"""

import os, re, json, sys, time, requests
from requests.auth import HTTPBasicAuth

# === CONFIG — EDIT THESE ===
BASE_URL = "https://tagsjapan.com/zh"
# If running ON the production server, change to:
# BASE_URL = "http://localhost/zh"

WP_USER = "tagsjapan.com"
WP_APP_PASS = "0afk iMAx ze7i aW9C YZ80 oo4o"

# === PATHS (local workspace — adjust if on another machine) ===
CONTENT_DIR = os.path.join(os.path.dirname(__file__), "zh-TW")

auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
headers = {"Content-Type": "application/json"}
TIMEOUT = 60
BATCH_SIZE = 5
DELAY = 0.3

# Category maps
TRAVEL_CATS = {
    "destinations": "目的地／地區", "transportation": "交通",
    "accommodation": "住宿", "food-drink": "飲食",
    "festivals-experiences": "節慶／體驗", "nature-outdoor": "自然／戶外",
    "hot-springs": "溫泉", "shopping-pop-culture": "購物／流行文化",
    "safety-practical": "安全／實務", "sustainable-special": "永續／特色體驗",
}
CULTURE_CATS = {
    "core_concept": "核心概念型", "aesthetic_thought": "美學／思想型",
    "historical_event": "歷史事件型", "historical_period": "歷史時期型",
    "institution_system": "制度／體制型", "social_structure": "社會結構型",
    "identity_group": "身份／群體型", "policy_strategy": "政策／國家戰略型",
    "organization_actor": "組織／行動者型", "contemporary_issue": "當代議題型",
    "unclassified": "未分類",
}

tag_cache = {}
cat_cache = {}

def get_or_create_category(slug, name, parent_slug=None):
    key = slug
    if key in cat_cache: return cat_cache[key]
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/categories", params={"slug": slug}, auth=auth, timeout=TIMEOUT)
    if r.status_code == 200 and r.json():
        cat_cache[key] = r.json()[0]["id"]
        return cat_cache[key]
    data = {"name": name, "slug": slug}
    if parent_slug:
        pid = get_or_create_category(parent_slug, "旅行" if parent_slug == "travel" else "認識日本")
        data["parent"] = pid
    r = requests.post(f"{BASE_URL}/wp-json/wp/v2/categories", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        cat_cache[key] = r.json()["id"]
        return r.json()["id"]
    print(f"  ⚠️ Cat fail: {slug}")
    return None

def get_or_create_tag(name):
    if name in tag_cache: return tag_cache[name]
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/tags", params={"search": name}, auth=auth, timeout=TIMEOUT)
    if r.status_code == 200 and r.json():
        for t in r.json():
            if t.get("name") == name:
                tag_cache[name] = t["id"]
                return t["id"]
    r = requests.post(f"{BASE_URL}/wp-json/wp/v2/tags", json={"name": name}, auth=auth, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        tag_cache[name] = r.json()["id"]
        return r.json()["id"]
    return None

def parse_file(filepath):
    with open(filepath) as f:
        content = f.read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not m:
        return None
    
    raw, body = m.group(1), m.group(2).strip()
    fm, tags, in_tags = {}, [], False
    
    for line in raw.split('\n'):
        t = line.strip()
        if t == 'tags:':
            in_tags = True; continue
        if in_tags:
            if t.startswith('- '):
                tags.append(t[2:].strip())
            else:
                in_tags = False
        if not in_tags and ':' in t and not t.startswith('- '):
            k, v = t.split(':', 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    
    return fm, body, tags

def push_one(filepath):
    result = parse_file(filepath)
    if not result:
        return None, "bad format"
    
    fm, body, tags_list = result
    title = fm.get('title', '')
    slug = fm.get('slug', '')
    seo = fm.get('genesis_description', '')
    excerpt = fm.get('excerpt', '')
    cat_slug = fm.get('category_slug', 'unclassified')
    wp_date = fm.get('wp_date', '')
    
    # Route category
    parent = 'understand-japan' if slug.startswith('understand-japan-') else 'travel'
    cat_map = CULTURE_CATS if parent == 'understand-japan' else TRAVEL_CATS
    cat_id = get_or_create_category(cat_slug, cat_map.get(cat_slug, '未分類'), parent)
    
    # Tags
    tag_ids = [get_or_create_tag(t) for t in tags_list[:8]
               if not t.strip().isdigit() and len(t.strip()) >= 2]
    tag_ids = [t for t in tag_ids if t]
    
    # Post data
    data = {
        "title": title, "slug": slug, "content": body,
        "excerpt": excerpt, "status": "publish",
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_genesis_title": "",
            "_genesis_description": seo,
            "_open_graph_title": title,
            "_open_graph_description": seo,
            "_twitter_title": title,
            "_twitter_description": seo,
            "_genesis_noindex": 0, "_genesis_nofollow": 0, "_genesis_noarchive": 0,
        },
    }
    if wp_date:
        data["date"] = wp_date.replace(" ", "T") + "+09:00"
    
    # Check existing
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/posts", params={"slug": slug, "status": "any"}, auth=auth, timeout=TIMEOUT)
    existing = r.json() if r.status_code == 200 else []
    
    if existing and len(existing) > 0:
        pid = existing[0]["id"]
        r = requests.put(f"{BASE_URL}/wp-json/wp/v2/posts/{pid}", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
        if r.status_code in [200, 201]:
            return pid, "update"
        return None, f"HTTP {r.status_code}"
    else:
        r = requests.post(f"{BASE_URL}/wp-json/wp/v2/posts", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
        if r.status_code == 201:
            return r.json()["id"], "create"
        return None, f"HTTP {r.status_code}: {r.text[:100]}"

def main():
    # Collect files
    files = []
    for root, dirs, fnames in os.walk(CONTENT_DIR):
        for f in fnames:
            if f.endswith('.md') and 'pure-md' not in root and not f.startswith('.'):
                files.append(os.path.join(root, f))
    files.sort()
    total = len(files)
    
    # Range filter
    start, end = 0, total
    for arg in sys.argv:
        if arg.startswith('--start='): start = int(arg.split('=')[1])
        if arg.startswith('--end='): end = int(arg.split('=')[1])
    files = files[start:end]
    
    created = updated = errors = 0
    print(f"Pushing {len(files)}/{total} articles to {BASE_URL}\n")
    
    for i in range(0, len(files), BATCH_SIZE):
        for fpath in files[i:i+BATCH_SIZE]:
            rel = os.path.relpath(fpath, CONTENT_DIR)
            pid, action = push_one(fpath)
            if pid:
                if action == "create":
                    created += 1
                    print(f"  CREATE #{pid} {rel}")
                else:
                    updated += 1
                    print(f"  UPDATE #{pid} {rel}")
            else:
                errors += 1
                print(f"  ❌ {rel}: {action}")
        
        if i % 20 == 0 and i > 0:
            print(f"\n→ {i}/{len(files)} | C:{created} U:{updated} E:{errors}\n")
        time.sleep(DELAY)
    
    print(f"\n{'='*50}")
    print(f"Done: {created} created, {updated} updated, {errors} errors")

if __name__ == '__main__':
    main()
