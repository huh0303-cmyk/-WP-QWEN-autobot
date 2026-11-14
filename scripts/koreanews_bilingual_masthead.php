<?php
/** Bilingual masthead for the Newsup desktop and mobile logo slots. */
add_filter('get_custom_logo', function ($logo) {
    return sprintf(
        '<a class="kn365-brand" href="%s" rel="home"><span class="kn365-brand-ko" lang="ko">한국신문</span><span class="kn365-brand-en" lang="en">Korea Newspaper</span><span class="kn365-brand-domain" lang="en">Koreanews365.com</span><span class="kn365-brand-imprint"><span>민족정론지</span><span>편집인: Chris Huh</span></span><span class="kn365-brand-imprint">창간일: 2020.11.02 · 서울, 대한민국</span></a>',
        esc_url(home_url('/'))
    );
}, PHP_INT_MAX);

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style('kn365-masthead-fonts', 'https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@900&family=Playfair+Display:wght@600;800&display=swap', array(), null);
});

add_action('wp_head', function () {
    ?>
    <style id="kn365-bilingual-masthead">
      .mg-headwidget a.kn365-brand{display:inline-grid!important;justify-items:center;gap:3px;padding:9px 14px 12px;color:#151310!important;text-align:center;text-decoration:none!important;white-space:nowrap}
      .mg-headwidget .header-ads,.mg-headwidget .row > div:has(> .header-ads),.mg-headwidget .adsbygoogle,.mg-headwidget .google-auto-placed{display:none!important}
      .mg-headwidget .mg-nav-widget-area-back .inner,.mg-headwidget .mg-nav-widget-area{background:#fff!important;background-image:none!important}
      .mg-headwidget .mg-nav-widget-area{padding:18px 0 12px!important;border-bottom:4px double #24211d!important}
      .mg-headwidget .row > div:has(.kn365-brand){flex:0 0 100%!important;max-width:100%!important;width:100%!important;text-align:center!important}
      .mg-headwidget .navbar-header,.mg-headwidget .site-logo{float:none!important;text-align:center!important;margin-inline:auto!important}
      .mg-headwidget .navbar-wp{border-top:0!important}
      body.home,body.blog,body.archive,body.single{background:#f0f0ef!important}
      #page.site{max-width:1460px;margin-inline:auto;background:#fff!important;border-inline:1px solid #d9d9d6}
      #page.site #content,.mg-headwidget{background:#fff!important}
      .kn365-brand-imprint{display:flex;justify-content:center;flex-wrap:wrap;column-gap:14px;row-gap:3px;margin-top:6px;color:#3d3934;font:700 12px/1.5 "Noto Serif KR","Nanum Myeongjo",Georgia,serif}
      .kn365-brand-imprint > span + span{border-left:1px solid #b9b6b0;padding-left:14px}
      @media(max-width:767px){#page.site{border-inline:0}.kn365-brand-imprint{font-size:11px}}
      .kn365-brand-ko{font:900 clamp(38px,7vw,86px)/1.08 "Noto Serif KR","Nanum Myeongjo",Batang,serif;letter-spacing:-.085em;padding-right:.085em}
      .kn365-brand-en{font:800 clamp(17px,2.8vw,29px)/1.25 "Playfair Display",Georgia,serif;letter-spacing:.015em}
      .kn365-brand-domain{margin-top:3px;padding-top:5px;border-top:1px solid #9e9281;font:600 clamp(11px,1.5vw,14px)/1.25 "Playfair Display",Georgia,serif;letter-spacing:.12em;color:#64352d}
      .mg-headwidget a.kn365-brand:focus-visible{outline:2px solid #64352d;outline-offset:4px}
      @media(max-width:575px){.mg-headwidget a.kn365-brand{padding:6px 8px 8px;gap:2px}}
    </style>
    <?php
}, 100);