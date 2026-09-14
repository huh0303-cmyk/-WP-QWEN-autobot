// ki-korea.com only: lighten the overly heavy title/header weight the site owner flagged.
add_action('wp_head', function () {
    echo '<style id="kikorea-title-style-fix-css">
    .entry-title{font-weight:600!important}
    .network-text-site-title{font-weight:500!important;font-size:clamp(20px,2.4vw,30px)!important}
    </style>';
}, 100);
