// Disable commenting/replies site-wide (all posts/pages, present and future).
// 2026-08-22 사용자 지시 — 모든 사이트에서 댓글/답글 작성 자체를 막는다.
// 개별 글마다 comment_status를 일일이 바꾸는 대신, 필터로 강제 차단해서
// 기존 글+새 글 전부 즉시 적용되게 한다(코어가 comments_open()==false면
// 댓글 폼도 자동으로 안 그림, 제출도 wp-comments-post.php에서 차단됨).

add_filter('comments_open', '__return_false', 20, 2);
add_filter('pings_open', '__return_false', 20, 2);
add_filter('notify_post_author', '__return_false');
add_filter('notify_moderator', '__return_false');

add_action('init', function () {
    update_option('default_comment_status', 'closed');
    update_option('default_ping_status', 'closed');
    update_option('comments_notify', 0);
    update_option('moderation_notify', 0);
});
