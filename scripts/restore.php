<?php
/**
 * Restore WordPress Site from wordpress-pre Archives
 * ==================================================
 * Usage: 
 *   wp --url=tagsjapan-com.local eval-file restore.php
 *   wp --url=tagsjapan-com.local/zh eval-file restore.php
 * 
 * This script reads all .md files from a directory and restores them as WordPress posts
 * with exact slugs, dates, categories, tags, and SEO metadata.
 * 
 * Directory structure expected:
 *   {base_dir}/{lang}/{series}/
 *   e.g. en/travel/001-hokkaido.md
 *        zh-TW/travel/001-hokkaido.md
 *        zh-TW/understand-japan/001-wa.md
 */

// --- CONFIG ---
// Pass the base directory as an argument or set it here
$base_dir = __DIR__ . '/..';
$lang = 'en'; // 'en' or 'zh-TW'

// Detect language from URL
$current_url = get_site_url();
if (strpos($current_url, '/zh') !== false || strpos($current_url, '/zh_TW') !== false) {
    $lang = 'zh-TW';
}

$series = ['travel', 'understand-japan'];

// --- CATEGORY DEFINITIONS ---
$travel_cats = [
    'destinations'           => ($lang == 'zh-TW' ? '目的地／地區' : 'Destinations'),
    'transportation'         => ($lang == 'zh-TW' ? '交通' : 'Transportation'),
    'accommodation'          => ($lang == 'zh-TW' ? '住宿' : 'Accommodation'),
    'food-drink'             => ($lang == 'zh-TW' ? '飲食' : 'Food & Drink'),
    'festivals-experiences'  => ($lang == 'zh-TW' ? '節慶／體驗' : 'Festivals & Experiences'),
    'nature-outdoor'         => ($lang == 'zh-TW' ? '自然／戶外' : 'Nature & Outdoor'),
    'hot-springs'            => ($lang == 'zh-TW' ? '溫泉' : 'Hot Springs'),
    'shopping-pop-culture'   => ($lang == 'zh-TW' ? '購物／流行文化' : 'Shopping & Pop Culture'),
    'safety-practical'       => ($lang == 'zh-TW' ? '安全／實務' : 'Safety & Practical'),
    'sustainable-special'    => ($lang == 'zh-TW' ? '永續／特色體驗' : 'Sustainable & Special'),
];

$culture_cats = [
    'core_concept'       => ($lang == 'zh-TW' ? '核心概念型' : 'Core Concepts'),
    'aesthetic_thought'  => ($lang == 'zh-TW' ? '美學／思想型' : 'Aesthetic Thought'),
    'historical_event'   => ($lang == 'zh-TW' ? '歷史事件型' : 'Historical Events'),
    'historical_period'  => ($lang == 'zh-TW' ? '歷史時期型' : 'Historical Periods'),
    'institution_system' => ($lang == 'zh-TW' ? '制度／體制型' : 'Institutions & Systems'),
    'social_structure'   => ($lang == 'zh-TW' ? '社會結構型' : 'Social Structures'),
    'identity_group'     => ($lang == 'zh-TW' ? '身份／群體型' : 'Identity & Groups'),
    'policy_strategy'    => ($lang == 'zh-TW' ? '政策／國家戰略型' : 'Policy & Strategy'),
    'organization_actor' => ($lang == 'zh-TW' ? '組織／行動者型' : 'Organizations & Actors'),
    'contemporary_issue' => ($lang == 'zh-TW' ? '當代議題型' : 'Contemporary Issues'),
    'unclassified'       => ($lang == 'zh-TW' ? '未分類' : 'Unclassified'),
];

// --- STEP 1: Ensure categories exist ---
$parent_cats = [
    'travel'            => 'Travel',
    'understand-japan'  => ($lang == 'zh-TW' ? '認識日本' : 'Understand Japan'),
];

foreach ($parent_cats as $pslug => $pname) {
    $parent = term_exists($pname, 'category');
    if (!$parent) {
        $parent = wp_insert_term($pname, 'category', ['slug' => $pslug]);
    }
    $pid = is_array($parent) ? $parent['term_id'] : $parent;
    
    $cats = ($pslug == 'travel') ? $travel_cats : $culture_cats;
    foreach ($cats as $slug => $name) {
        $term = term_exists($name, 'category');
        if (!$term) {
            $term = wp_insert_term($name, 'category', ['slug' => $slug, 'parent' => $pid]);
        }
    }
}

echo "Categories ready.\n";

// --- STEP 2: Process all post files ---
$total = 0;
$errors = 0;

foreach ($series as $s) {
    $dir = "{$base_dir}/{$lang}/{$s}";
    if (!is_dir($dir)) {
        echo "Directory not found: {$dir}\n";
        continue;
    }
    
    $files = glob("{$dir}/*.md");
    sort($files);
    
    foreach ($files as $filepath) {
        $content = file_get_contents($filepath);
        if (!preg_match('/^---\n(.*?)\n---\n(.*)/s', $content, $m)) {
            echo "[SKIP] " . basename($filepath) . ": bad format\n";
            $errors++;
            continue;
        }
        
        // Parse frontmatter
        $raw = $m[1];
        $body = trim($m[2]);
        $fm = [];
        $tags = [];
        
        foreach (explode("\n", $raw) as $line) {
            $trimmed = trim($line);
            if (empty($trimmed) || $trimmed[0] === '#') continue;
            if (preg_match('/^\s+-\s+(.+)/', $line, $m2)) {
                $tags[] = trim($m2[1]);
                continue;
            }
            if (preg_match('/^([a-z_]+):\s*(.*)/', $trimmed, $m2)) {
                $key = $m2[1];
                $val = trim($m2[2], " \"'");
                if ($key !== 'tags') {
                    $fm[$key] = $val;
                }
            }
        }
        
        $title    = $fm['title'] ?? basename($filepath, '.md');
        $slug     = $fm['slug'] ?? '';
        $wp_date  = $fm['wp_date'] ?? date('Y-m-d H:i:s');
        $status   = $fm['wp_status'] ?? 'draft';
        $excerpt  = $fm['excerpt'] ?? '';
        $seo_desc = $fm['genesis_description'] ?? '';
        $cat_slug = $fm['category_slug'] ?? 'uncategorized';
        
        // Find category ID
        $cat_id = 1;
        $cat_names = ($s == 'travel') ? $travel_cats : $culture_cats;
        if (isset($cat_names[$cat_slug])) {
            $term = term_exists($cat_names[$cat_slug], 'category');
            if ($term) {
                $cat_id = is_array($term) ? $term['term_id'] : $term;
            }
        }
        
        // Create post with exact date
        $post_id = wp_insert_post([
            'post_title'    => $title,
            'post_name'     => $slug,
            'post_content'  => $body,
            'post_excerpt'  => $excerpt,
            'post_date'     => $wp_date,
            'post_date_gmt' => $wp_date,
            'post_status'   => $status,
            'post_author'   => 1,
            'meta_input'    => [
                '_genesis_title'          => '',
                '_genesis_description'    => $seo_desc,
                '_open_graph_title'       => $title,
                '_open_graph_description' => $seo_desc,
                '_twitter_title'          => $title,
                '_twitter_description'    => $seo_desc,
                '_genesis_noindex'        => 0,
                '_genesis_nofollow'       => 0,
                '_genesis_noarchive'      => 0,
            ],
        ], true);
        
        if (is_wp_error($post_id)) {
            echo "[FAIL] {$title}: " . $post_id->get_error_message() . "\n";
            $errors++;
            continue;
        }
        
        // Set category
        wp_set_post_categories($post_id, [$cat_id], false);
        
        // Set tags (as string names, avoids term_exists() numeric bug)
        $clean_tags = [];
        foreach ($tags as $t) {
            $t = trim($t);
            if (!is_numeric($t) && strlen($t) >= 2) {
                $clean_tags[] = $t;
            }
        }
        if (!empty($clean_tags)) {
            wp_set_post_tags($post_id, $clean_tags, false);
        }
        
        $total++;
    }
}

echo "\n=== Restore Complete: {$total} posts, {$errors} errors ===\n";
