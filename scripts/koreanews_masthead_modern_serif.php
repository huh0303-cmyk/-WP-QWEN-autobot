<?php
/** Modern serif masthead and restrained newsprint treatment for Koreanews365. */

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style(
        'kn365-noto-serif-kr',
        'https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;600;700;800&display=swap',
        array(),
        null
    );
}, 20);

add_action('wp_head', function () {
    if (is_admin()) {
        return;
    }
    ?>
    <style id="kn365-modern-masthead">
      .mg-nav-widget-area-back{
        background:#fff!important;
        background-image:none!important;
        border:0!important;
        border-bottom:1px solid #e7e7e7!important;
        box-shadow:none!important;
      }
      .mg-nav-widget-area-back .overlay{background:transparent!important;padding:26px 0 24px!important}
      .mg-nav-widget-area .navbar-header,.mg-nav-widget-area .site-branding-text{float:none!important;width:100%!important;text-align:center!important}
      .mg-nav-widget-area .site-title,.mg-nav-widget-area .site-title a{
        font-family:"Noto Serif KR","Nanum Myeongjo",serif!important;
        color:#171511!important;
        font-size:40px!important;
        font-weight:700!important;
        line-height:1.2!important;
        letter-spacing:.14em!important;
        text-shadow:none!important;
      }
      .mg-nav-widget-area .site-description{
        display:block!important;
        margin:9px 0 0!important;
        font-family:"Noto Serif KR","Nanum Myeongjo",serif!important;
        color:#4b463d!important;
        font-size:12px!important;
        font-weight:600!important;
        line-height:1.5!important;
        letter-spacing:.22em!important;
        text-shadow:none!important;
      }
      .mg-head-detail,.mg-head-detail .container-fluid,.mg-headwidget,.mg-headwidget .navbar-wp,.mg-headwidget .navbar-wp .navbar-nav,.mg-headwidget .navbar-wp .navbar-header{background:#fff!important;background-image:none!important}
      .mg-head-detail{border-bottom:1px solid #eeeeee!important}
      .mg-head-detail,.mg-head-detail a,.mg-head-detail li,.mg-headwidget .navbar-wp .navbar-nav>li>a,.mg-headwidget .navbar-wp .navbar-brand{color:#171717!important;text-shadow:none!important}
      .mg-headwidget .navbar-wp .navbar-nav>.active>a,.mg-headwidget .navbar-wp .navbar-nav>li>a:hover,.mg-headwidget .navbar-wp .navbar-nav>li>a:focus{background:#fff!important;color:#111!important;box-shadow:inset 0 -2px #111!important}
      .mg-headwidget .navbar-wp{border-top:0!important;border-bottom:1px solid #e7e7e7!important;box-shadow:none!important}
      @media(max-width:767px){
        .mg-nav-widget-area-back .overlay{padding:20px 0 18px!important}
        .mg-nav-widget-area .site-title,.mg-nav-widget-area .site-title a{font-size:32px!important;letter-spacing:.11em!important}
        .mg-nav-widget-area .site-description{font-size:11px!important;letter-spacing:.16em!important}
      }
    </style>
    <?php
}, 35);
