# Tags Japan Content Archives

Full-content backup of **Tags Japan** (English) and **讀記日本** (Traditional Chinese) — two WordPress Multisite sites with 1,160 articles covering Japanese travel and culture.

## Structure

```
tagsjapan-content/
├── en/                        # Tags Japan (main site, English)
│   ├── travel/                #   260 travel articles
│   ├── understand-japan/      #   320 culture/deep-dive articles
│   └── pure-md/               #   Raw markdown (no frontmatter)
│
├── zh-TW/                     # 讀記日本 (/zh/ subsite, Traditional Chinese)
│   ├── travel/                #   260 travel articles
│   ├── understand-japan/      #   320 culture articles
│   └── pure-md/               #   Raw markdown
│
└── scripts/
    ├── restore.php            #   Full site restore from wordpress-pre files
    └── setup.php              #   Initial setup (plugins, theme, categories)
```

## File Format (wordpress-pre)

Each `.md` file is self-contained with YAML frontmatter:

```yaml
---
title: "Hokkaido"
slug: travel-hokkaido              # Same slug across English and Chinese
wp_date: 2025-01-01 09:00:00       # Exact publish timestamp
wp_status: publish                 # publish / draft
wp_blog_id: 1                      # 1 = English main site, 2 = /zh/ subsite

category_name: Destinations
category_slug: destinations         # Same slug in English and Chinese

tags:
  - Hokkaido
  - Winter Travel
  - Shiretoko

excerpt: "First paragraph for readers..."
genesis_description: "SEO description 120-160 chars..."
genesis_title: ""                   # Empty = TSF auto-stitches
open_graph_title: "Hokkaido"
open_graph_description: "..."
twitter_title: "Hokkaido"
twitter_description: "..."
genesis_noindex: 0
genesis_nofollow: 0
genesis_noarchive: 0
---

# Article content starts here (Markdown)
```

## Restore from Scratch

After a fresh WordPress installation with The SEO Framework, HorsePress theme, and Classic Editor:

```bash
# English site (main)
wp eval-file scripts/restore.php

# Chinese site (/zh/ subsite)
wp --url=http://example.com/zh eval-file scripts/restore.php
```

The script auto-detects the language from the site URL and:
1. Creates all categories (Travel / Understand Japan + subcategories)
2. Creates all posts with exact slugs and dates
3. Assigns tags
4. Sets all TSF SEO metadata

## Key Facts

| | English | Chinese |
|---|---|---|
| **Site** | Tags Japan | 讀記日本 |
| **Theme** | HorsePress | HorsePress |
| **Articles** | 580 | 580 |
| **Tags** | English-only nouns | Mixed zh/en/ja |
| **Categories** | Travel (10) + Understand Japan (11) | Same slugs |
| **Date range** | 2025-01-01 → 2026-08-03 | 2025-06-01 → 2026-07-25 |
| **SEO** | The SEO Framework | TSF + tsf-rest-meta-bridge |

## Slug Convention

- Travel: `travel-{keyword_en}` (e.g., `travel-hokkaido`)
- Culture: `understand-japan-{keyword_en}` (e.g., `understand-japan-wa`)

Slugs are **identical** between English and Chinese versions — only the language of the content differs.
