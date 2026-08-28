// Daily visitor counter v3 — footer display + read-only REST endpoint.
// 2026-08-21 최초 배포, 2026-08-22 강화, 2026-08-26 일일 종합상황실용
// 전날/전전날 확정 방문자수 추가. Footer 표시는 기존처럼 오늘/누적을 유지한다.
// 봇 트래픽 제외, 쿠키 기반 일일 중복방지(페이지뷰가 아닌 방문자 근사치).

add_action('wp_footer', function () {
    if (is_admin()) return;

    $ua = isset($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '';
    if ($ua === '' || preg_match('/bot|crawl|spider|slurp|bingpreview|facebookexternalhit|pingdom|uptime|ahrefs|semrush|mj12/i', $ua)) {
        return;
    }

    // 전체 네트워크는 WordPress 개별 timezone 설정과 무관하게 KST 기준으로 집계한다.
    $today = wp_date('Y-m-d', null, new DateTimeZone('Asia/Seoul'));
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
            $kst = new DateTimeZone('Asia/Seoul');
            $today = wp_date('Y-m-d', null, $kst);
            $yesterday = wp_date('Y-m-d', time() - DAY_IN_SECONDS, $kst);
            $day_before_yesterday = wp_date('Y-m-d', time() - (2 * DAY_IN_SECONDS), $kst);
            return array(
                // 기존 소비 코드 호환: count는 오늘 현재값 유지.
                'date' => $today,
                'count' => (int) get_option('daily_visitor_count_' . $today, 0),
                'yesterday_date' => $yesterday,
                'yesterday_count' => (int) get_option('daily_visitor_count_' . $yesterday, 0),
                'day_before_yesterday_date' => $day_before_yesterday,
                'day_before_yesterday_count' => (int) get_option('daily_visitor_count_' . $day_before_yesterday, 0),
                'total' => (int) get_option('daily_visitor_total_all_time', 0),
            );
        },
        'permission_callback' => '__return_true',
    ));
});
