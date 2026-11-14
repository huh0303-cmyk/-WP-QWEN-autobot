<?php
/** Bilingual masthead for the Newsup desktop and mobile logo slots. */
add_filter('get_custom_logo', function ($logo) {
    return sprintf(
        '<a class="kn365-brand" href="%s" rel="home"><span class="kn365-side kn365-left"><span>Koreanews365.com</span><span>편집인: Chris Huh</span></span><span class="kn365-center"><span class="kn365-motto">민족정론지</span><span class="kn365-brand-ko" lang="ko">한국신문</span><span class="kn365-brand-en" lang="en">Korea Newspaper</span></span><span class="kn365-side kn365-right"><span>창간일: 2020.11.02</span><span>서울, 대한민국</span></span></a>',
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
      .kn365-brand-ko{font:900 clamp(38px,7vw,86px)/1.08 "Noto Serif KR","Nanum Myeongjo",Batang,serif;letter-spacing:-.085em;padding-right:.085em}
      .kn365-brand-en{font:800 clamp(17px,2.8vw,29px)/1.25 "Playfair Display",Georgia,serif;letter-spacing:.015em}
      .mg-headwidget a.kn365-brand:focus-visible{outline:2px solid #64352d;outline-offset:4px}
      @media(max-width:575px){.mg-headwidget a.kn365-brand{padding:6px 8px 8px;gap:2px}}
      .mg-headwidget a.kn365-brand{width:min(100%,1060px);grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:end;gap:clamp(8px,3vw,48px);box-sizing:border-box}
      .kn365-center,.kn365-side{display:grid;gap:4px}
      .kn365-motto{font:900 13px/1.4 "Noto Serif KR",serif;letter-spacing:.18em}
      .kn365-side{font:700 13px/1.45 Georgia,"Noto Serif KR",serif;color:#49443d}
      .kn365-left{justify-self:start;text-align:left}
      .kn365-right{justify-self:end;text-align:right}
      @media(max-width:575px){.mg-headwidget a.kn365-brand{grid-template-columns:1fr 1fr;row-gap:12px}.kn365-center{grid-column:1/-1;grid-row:1}.kn365-side{font-size:11px}}
    </style>
    <?php
}, 100);