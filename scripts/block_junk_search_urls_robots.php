// Block crawling of internal search / tag-feed-search combo URLs that waste
// crawl budget on junk near-duplicate pages (e.g. /tag/x/feed/?s=query).
// 2026-08-22 사용자 지시 — kfinance365에서 발견된 패턴, 전체 사이트 적용.
// 진짜 RSS 피드(/feed/, 사이트맵으로 이미 제출됨)는 그대로 허용, 검색
// 쿼리(?s=)가 붙은 것만 차단한다.

add_filter('robots_txt', function ($output, $public) {
    if ((int) $public !== 1) {
        return $output;
    }
    $output .= "\n# Block internal search / search+feed combo URLs (crawl budget waste)\n";
    $output .= "Disallow: /*?s=\n";
    $output .= "Disallow: /*?*&s=\n";
    return $output;
}, 20, 2);
