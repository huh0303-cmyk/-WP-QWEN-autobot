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
      html,body,.wrapper,.container-fluid.home,.mg-posts-sec,.mg-posts-sec-inner{
        background:#fff!important;
      }
      .mg-nav-widget-area-back,.mg-nav-widget-area-back .overlay,.mg-headwidget,.mg-menu-full,.navbar-wp{
        background-color:#fff!important;
      }
      .bn_title{
        width:142px!important;
        min-width:142px!important;
        height:40px!important;
        background:#cf142b!important;
      }
      .bn_title .title{
        display:flex!important;
        flex-direction:row!important;
        align-items:center!important;
        justify-content:center!important;
        gap:8px!important;
        width:142px!important;
        min-width:142px!important;
        height:40px!important;
        margin:0!important;
        color:#fff!important;
        white-space:nowrap!important;
      }
      .bn_title .kn365-breaking-word{
        display:inline-block!important;
        width:auto!important;
        height:auto!important;
        color:#fff!important;
        font-size:15px!important;
        font-weight:800!important;
        line-height:1!important;
        letter-spacing:.14em!important;
        opacity:1!important;
        visibility:visible!important;
      }
      .bn_title .kn365-breaking-bolt{display:inline-block!important;font-size:17px!important;line-height:1!important}
      .mg-posts-sec-inner{
        display:grid!important;
        grid-template-columns:repeat(2,minmax(0,1fr))!important;
        gap:22px!important;
        width:100%!important;
        margin:0!important;
      }
      .mg-posts-sec-inner>article.mg-posts-sec-post{
        display:flex!important;
        flex-direction:column!important;
        float:none!important;
        width:auto!important;
        max-width:none!important;
        min-width:0!important;
        box-sizing:border-box!important;
        height:auto!important;
        margin:0!important;
        padding:0!important;
        align-items:flex-start!important;
        background:#fff!important;
        border:1px solid #e5e7eb!important;
        border-radius:14px!important;
        overflow:hidden!important;
        box-shadow:0 7px 22px rgba(15,23,42,.055)!important;
      }
      .mg-posts-sec-inner>article.mg-posts-sec-post>.col-12.col-md-6{
        flex:0 0 100%!important;
        width:100%!important;
        max-width:none!important;
        padding:0!important;
      }
      .mg-posts-sec-inner>article .mg-post-thumb{
        width:100%!important;
        height:auto!important;
        min-height:0!important;
        aspect-ratio:16/9!important;
        background-size:cover!important;
        background-position:center!important;
        border-radius:0!important;
      }
      .mg-posts-sec-inner>article .mg-sec-top-post{
        width:100%!important;
        flex:0 0 auto!important;
        padding:20px 22px 22px!important;
      }
      .mg-posts-sec-inner>article .title{font-size:21px!important;line-height:1.42!important}
      .mg-posts-sec-inner>article .mg-blog-meta{font-size:12px!important}
      .mg-posts-sec-inner>article .mg-content{font-size:15px!important;line-height:1.85!important}
      @media(max-width:820px){
        .mg-posts-sec-inner{grid-template-columns:1fr!important;gap:16px!important}
        .mg-posts-sec-inner>article .mg-sec-top-post{padding:18px!important}
      }
    </style>
    <?php
}, 99);
