<?php
/** Koreanews365 breaking-label cleanup for the Newsup theme. */

add_action('wp_footer', function () {
    if (is_admin()) {
        return;
    }
    ?>
    <style id="kn365-breaking-label-style">
      a.newsup-categories[href*="/category/breaking/"]{display:none!important}
      .bn_title .title{display:flex!important;flex-direction:row!important;align-items:center!important;justify-content:center!important;gap:8px;min-width:116px;white-space:nowrap}
      .bn_title .title:before,.bn_title .title:after{display:none!important;content:none!important}
      .bn_title .kn365-breaking-bolt{display:inline-block;color:#fff;font-size:17px;line-height:1;animation:kn365-bolt-blink 1s step-end infinite}
      .bn_title .kn365-breaking-word{display:inline-block;color:#fff;font-weight:800;letter-spacing:.18em;line-height:1}
      @keyframes kn365-bolt-blink{0%,54%{opacity:1;filter:drop-shadow(0 0 3px rgba(255,255,255,.75))}55%,100%{opacity:.2;filter:none}}
      @media (prefers-reduced-motion:reduce){.bn_title .kn365-breaking-bolt{animation:none}}
    </style>
    <script id="kn365-breaking-label-script">
      document.addEventListener('DOMContentLoaded',function(){
        const label=document.querySelector('.bn_title .title');
        if(label) label.innerHTML='<span class="kn365-breaking-bolt" aria-hidden="true">⚡</span><span class="kn365-breaking-word">속 보</span>';
      });
    </script>
    <?php
}, 55);
