<?php
/** Koreanews365 two-column archive grid and deeper published archive. */

add_action('pre_get_posts', function ($query) {
    if (is_admin() || !$query->is_main_query() || !$query->is_home()) return;
    $query->set('posts_per_page', 20);
    $query->set('post_status', 'publish');
}, 20);

add_action('wp_head', function () {
    if (!is_home()) return;
    ?>
    <style id="kn365-home-two-column">
      .mg-posts-sec-inner{
        display:grid!important;
        grid-template-columns:repeat(2,minmax(0,1fr))!important;
        gap:22px!important;
        width:100%!important;
        margin:0!important;
      }
      .mg-posts-sec-inner>article.mg-posts-sec-post{
        float:none!important;
        width:100%!important;
        max-width:none!important;
        min-width:0!important;
        height:auto!important;
        margin:0!important;
        padding:24px!important;
        align-items:flex-start!important;
        background:#fff!important;
        border:1px solid #e5e7eb!important;
        border-radius:14px!important;
        box-shadow:0 7px 22px rgba(15,23,42,.055)!important;
      }
      .mg-posts-sec-inner>article .mg-sec-top-post{
        width:100%!important;
      }
      .mg-posts-sec-inner>article .title{font-size:21px!important;line-height:1.42!important}
      .mg-posts-sec-inner>article .mg-blog-meta{font-size:12px!important}
      .mg-posts-sec-inner>article .mg-content{font-size:15px!important;line-height:1.85!important}
      @media(max-width:820px){
        .mg-posts-sec-inner{grid-template-columns:1fr!important;gap:16px!important}
        .mg-posts-sec-inner>article.mg-posts-sec-post{padding:20px!important}
      }
    </style>
    <?php
}, 99);
