// Daily visitor counter — footer display + read-only REST endpoint.
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

    $today = date('Y-m-d');
    $day_key = 'daily_visitor_count_' . $today;
    $total_key = 'daily_visitor_total_all_time';

    if (!isset($_COOKIE['dvc_counted'])) {
        $day_count = (int) get_option($day_key, 0) + 1;
        update_option($day_key, $day_count, false);
        $total_count = (int) get_option($total_key, 0) + 1;
        update_option($total_key, $total_count, false);
        if (!headers_sent()) {
            setcookie('dvc_counted', '1', time() + 86400, '/');
        }
    } else {
        $day_count = (int) get_option($day_key, 0);
        $total_count = (int) get_option($total_key, 0);
    }

    echo '<div style="display:flex;justify-content:center;gap:14px;align-items:center;'
        . 'margin:18px auto 4px;padding:8px 16px;max-width:320px;border-radius:20px;'
        . 'background:rgba(120,120,120,0.08);font-size:12.5px;color:inherit;opacity:0.75;">'
        . '<span>👁 Today ' . number_format($day_count) . '</span>'
        . '<span style="opacity:0.5;">·</span>'
        . '<span>Total ' . number_format($total_count) . '</span>'
        . '</div>';
});

add_action('rest_api_init', function () {
    register_rest_route('site-stats/v1', '/visitors', array(
        'methods' => 'GET',
        'callback' => function () {
            $today = date('Y-m-d');
            return array(
                'date' => $today,
                'count' => (int) get_option('daily_visitor_count_' . $today, 0),
                'total' => (int) get_option('daily_visitor_total_all_time', 0),
            );
        },
        'permission_callback' => '__return_true',
    ));
});
