// Daily visitor counter — footer display + read-only REST endpoint.
// 2026-08-21 사용자 지시: 27개 사이트 전부 푸터에 일일 방문자수 노출 +
// 종합상황실 이메일 리포트에서 매일 조회할 수 있는 공개 REST 엔드포인트 제공.
// 쿠키 기반 중복방지(완벽하진 않지만 페이지뷰가 아닌 방문자 근사치로 충분).

add_action('wp_footer', function () {
    if (is_admin()) return;
    $today = date('Y-m-d');
    $key = 'daily_visitor_count_' . $today;
    if (!isset($_COOKIE['dvc_counted'])) {
        $count = (int) get_option($key, 0);
        update_option($key, $count + 1, false);
        if (!headers_sent()) {
            setcookie('dvc_counted', '1', time() + 86400, '/');
        }
    }
    $count = (int) get_option($key, 0);
    echo '<div style="text-align:center;padding:10px 0;font-size:12px;opacity:0.6;">'
        . 'Today\'s visitors: ' . number_format($count) . '</div>';
});

add_action('rest_api_init', function () {
    register_rest_route('site-stats/v1', '/visitors', array(
        'methods' => 'GET',
        'callback' => function () {
            $today = date('Y-m-d');
            $count = (int) get_option('daily_visitor_count_' . $today, 0);
            return array('date' => $today, 'count' => $count);
        },
        'permission_callback' => '__return_true',
    ));
});
