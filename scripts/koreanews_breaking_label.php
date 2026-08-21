<?php
/** Koreanews365 breaking-label cleanup for the Newsup theme. */

add_action('wp_footer', function () {
    if (is_admin()) {
        return;
    }
    ?>
    <style id="kn365-breaking-label-style">
      a.newsup-categories[href*="/category/breaking/"]{display:none!important}
      .bn_title .title{display:flex!important;align-items:center;justify-content:center;min-width:116px}
      .bn_title .kn365-breaking-word{color:#fff;font-weight:800;letter-spacing:.18em;animation:kn365-breaking-blink 1.25s step-end infinite}
      @keyframes kn365-breaking-blink{0%,55%{opacity:1}56%,100%{opacity:.28}}
      @media (prefers-reduced-motion:reduce){.bn_title .kn365-breaking-word{animation:none}}
    </style>
    <script id="kn365-breaking-label-script">
      document.addEventListener('DOMContentLoaded',function(){
        const label=document.querySelector('.bn_title .title');
        if(label) label.innerHTML='<span class="kn365-breaking-word">속보</span>';
      });
    </script>
    <?php
}, 45);
