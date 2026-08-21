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
        background-color:#f4efe3!important;
        background-image:
          radial-gradient(circle at 17% 24%,rgba(78,64,44,.045) 0 1px,transparent 1.4px),
          radial-gradient(circle at 78% 67%,rgba(78,64,44,.035) 0 1px,transparent 1.3px),
          repeating-linear-gradient(0deg,rgba(60,48,32,.016) 0,rgba(60,48,32,.016) 1px,transparent 1px,transparent 4px)!important;
        background-size:23px 19px,31px 27px,100% 4px!important;
        border-top:1px solid #28241d;
        border-bottom:3px double #28241d;
        box-shadow:inset 0 1px rgba(255,255,255,.72),inset 0 -1px rgba(45,38,28,.08);
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
      @media(max-width:767px){
        .mg-nav-widget-area-back .overlay{padding:20px 0 18px!important}
        .mg-nav-widget-area .site-title,.mg-nav-widget-area .site-title a{font-size:32px!important;letter-spacing:.11em!important}
        .mg-nav-widget-area .site-description{font-size:11px!important;letter-spacing:.16em!important}
      }
    </style>
    <?php
}, 25);
