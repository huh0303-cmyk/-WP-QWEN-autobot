// Daily visitor counter v2 — footer display + read-only REST endpoint.
// 2026-08-21 최초 배포, 2026-08-22 강화(사용자 지시 "일일방문자 세게 해주고"):
// 봇 트래픽 제외, 일일 수치와 함께 누적 총 방문자수도 같이 노출(신뢰 신호 강화),
// 눈에 띄는 배지 스타일로 교체(기존 opacity:0.6 회색 텍스트는 존재감이 없었음).
// 쿠키 기반 중복방지(완벽하진 않지만 페이지뷰가 아닌 방문자 근사치로 충분).

add_action('wp_footer', function () {
    if (is_admin()) return;

    $ua = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
    if ($ua === '' || preg_match('/bot|crawl|spider|slurp|bingpreview|facebookexternalhit|pingdom|uptime|ahrefs|semrush|mj12/i', $ua)) {
        return;
    }

    // Respect the site's WordPress timezone instead of the hosting server timezone.
    $today = current_time('Y-m-d');
    $day_key = 'daily_visitor_count_' . $today;
    $total_key = 'daily_visitor_total_all_time';
    $cookie_key = 'dvc_counted_' . str_replace('-', '', $today);

    if (!isset($_COOKIE[$cookie_key])) {
        $day_count = (int) get_option($day_key, 0) + 1;
        update_option($day_key, $day_count, false);
        $total_count = (int) get_option($total_key, 0) + 1;
        update_option($total_key, $total_count, false);
        if (!headers_sent()) {
            setcookie($cookie_key, '1', time() + DAY_IN_SECONDS, '/', '', is_ssl(), true);
        }
    } else {
        $day_count = (int) get_option($day_key, 0);
        $total_count = (int) get_option($total_key, 0);
    }

    $is_ko = strpos(determine_locale(), 'ko') === 0;
    $today_label = $is_ko ? '오늘 방문' : 'Today';
    $total_label = $is_ko ? '누적' : 'Total';
    echo '<div class="network-daily-visitor-counter" aria-label="Daily visitor counter" '
        . 'style="display:flex;justify-content:center;gap:14px;align-items:center;'
        . 'margin:18px auto 4px;padding:8px 16px;max-width:320px;border-radius:20px;'
        . 'background:rgba(120,120,120,0.08);font-size:12.5px;color:inherit;opacity:0.82;">'
        . '<span>👁 ' . esc_html($today_label) . ' ' . number_format_i18n($day_count) . '</span>'
        . '<span style="opacity:0.5;">·</span>'
        . '<span>' . esc_html($total_label) . ' ' . number_format_i18n($total_count) . '</span>'
        . '</div>';
});

add_action('rest_api_init', function () {
    register_rest_route('site-stats/v1', '/visitors', array(
        'methods' => 'GET',
        'callback' => function () {
            $today = current_time('Y-m-d');
            return array(
                'date' => $today,
                'count' => (int) get_option('daily_visitor_count_' . $today, 0),
                'total' => (int) get_option('daily_visitor_total_all_time', 0),
            );
        },
        'permission_callback' => '__return_true',
    ));
});
