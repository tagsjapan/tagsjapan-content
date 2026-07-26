#!/usr/bin/env python3
"""
Push EN content to tagsjapan.com via REST API.
Run ON the production server for best speed.

Usage:
  python3 push_en.py              # Push all 580 articles
  python3 push_en.py --start=0 --end=10

Config: Edit BASE_URL and WP_APP_PASS below.
"""

import os, re, sys, time, requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://tagsjapan.com"
WP_USER = "tagsjapan.com"
WP_APP_PASS = "mAba klP1 9UVH wM41 jgZE 5vSn"

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "en")
auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
headers = {"Content-Type": "application/json"}
TIMEOUT = 60
BATCH_SIZE = 5
DELAY = 0.3

TRAVEL_CATS = {"destinations":"Destinations","transportation":"Transportation","accommodation":"Accommodation","food-drink":"Food & Drink","festivals-experiences":"Festivals & Experiences","nature-outdoor":"Nature & Outdoor","hot-springs":"Hot Springs","shopping-pop-culture":"Shopping & Pop Culture","safety-practical":"Safety & Practical","sustainable-special":"Sustainable & Special"}
CULTURE_CATS = {"core_concept":"Core Concepts","aesthetic_thought":"Aesthetic Thought","historical_event":"Historical Events","historical_period":"Historical Periods","institution_system":"Institutions & Systems","social_structure":"Social Structures","identity_group":"Identity & Groups","policy_strategy":"Policy & Strategy","organization_actor":"Organizations & Actors","contemporary_issue":"Contemporary Issues","unclassified":"Unclassified"}

tag_cache = {}
cat_cache = {}

def get_or_create_category(slug, name, parent_slug=None):
    key = slug
    if key in cat_cache: return cat_cache[key]
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/categories", params={"slug": slug}, auth=auth, timeout=TIMEOUT)
    if r.status_code == 200 and r.json():
        cat_cache[key] = r.json()[0]["id"]; return cat_cache[key]
    data = {"name": name, "slug": slug}
    if parent_slug:
        pid = get_or_create_category(parent_slug, "Travel" if parent_slug=="travel" else "Understand Japan")
        data["parent"] = pid
    r = requests.post(f"{BASE_URL}/wp-json/wp/v2/categories", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        cat_cache[key] = r.json()["id"]; return r.json()["id"]
    return None

def get_or_create_tag(name):
    if name in tag_cache: return tag_cache[name]
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/tags", params={"search": name}, auth=auth, timeout=TIMEOUT)
    if r.status_code == 200 and r.json():
        for t in r.json():
            if t.get("name") == name:
                tag_cache[name] = t["id"]; return t["id"]
    r = requests.post(f"{BASE_URL}/wp-json/wp/v2/tags", json={"name": name}, auth=auth, headers=headers, timeout=TIMEOUT)
    if r.status_code == 201:
        tag_cache[name] = r.json()["id"]; return r.json()["id"]
    return None

def parse_file(filepath):
    with open(filepath) as f:
        content = f.read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not m: return None
    raw, body = m.group(1), m.group(2).strip()
    fm, tags, in_tags = {}, [], False
    for line in raw.split('\n'):
        t = line.strip()
        if t == 'tags:': in_tags = True; continue
        if in_tags:
            if t.startswith('- '): tags.append(t[2:].strip())
            else: in_tags = False
        if not in_tags and ':' in t and not t.startswith('- '):
            k, v = t.split(':', 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body, tags

def push_one(filepath):
    result = parse_file(filepath)
    if not result: return None, "bad format"
    fm, body, tags_list = result
    title, slug = fm.get('title',''), fm.get('slug','')
    seo, excerpt = fm.get('genesis_description',''), fm.get('excerpt','')
    cat_slug, wp_date = fm.get('category_slug','unclassified'), fm.get('wp_date','')
    
    parent = 'understand-japan' if slug.startswith('understand-japan-') else 'travel'
    cat_map = CULTURE_CATS if parent == 'understand-japan' else TRAVEL_CATS
    cat_id = get_or_create_category(cat_slug, cat_map.get(cat_slug,'Unclassified'), parent)
    
    tag_ids = [get_or_create_tag(t) for t in tags_list[:8] if not t.strip().isdigit() and len(t.strip())>=2]
    tag_ids = [t for t in tag_ids if t]
    
    data = {
        "title": title, "slug": slug, "content": body, "excerpt": excerpt,
        "status": "publish", "categories": [cat_id] if cat_id else [], "tags": tag_ids,
        "meta": {"_genesis_title":"","_genesis_description":seo,"_open_graph_title":title,
                 "_open_graph_description":seo,"_twitter_title":title,"_twitter_description":seo,
                 "_genesis_noindex":0,"_genesis_nofollow":0,"_genesis_noarchive":0},
    }
    if wp_date: data["date"] = wp_date.replace(" ","T")+"+09:00"
    
    r = requests.get(f"{BASE_URL}/wp-json/wp/v2/posts", params={"slug":slug,"status":"any"}, auth=auth, timeout=TIMEOUT)
    existing = r.json() if r.status_code == 200 else []
    if existing and len(existing)>0:
        pid = existing[0]["id"]
        r = requests.put(f"{BASE_URL}/wp-json/wp/v2/posts/{pid}", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
        return (pid, "update") if r.status_code in [200,201] else (None, f"HTTP {r.status_code}")
    else:
        r = requests.post(f"{BASE_URL}/wp-json/wp/v2/posts", json=data, auth=auth, headers=headers, timeout=TIMEOUT)
        return (r.json()["id"], "create") if r.status_code == 201 else (None, f"HTTP {r.status_code}")

def main():
    files = []
    for root, dirs, fnames in os.walk(CONTENT_DIR):
        for f in fnames:
            if f.endswith('.md') and 'pure-md' not in root and not f.startswith('.'):
                files.append(os.path.join(root, f))
    files.sort()
    total = len(files)
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
                if action == "create": created += 1; print(f"  CREATE #{pid} {rel}")
                else: updated += 1; print(f"  UPDATE #{pid} {rel}")
            else:
                errors += 1; print(f"  ❌ {rel}: {action}")
        if i % 20 == 0 and i > 0:
            print(f"\n→ {i}/{len(files)} | C:{created} U:{updated} E:{errors}\n")
        time.sleep(DELAY)
    print(f"\nDone: {created} created, {updated} updated, {errors} errors")

if __name__ == '__main__':
    main()
