// Network rule: header uses the site title as text, never a logo image.
add_filter('get_custom_logo', function ($html) {
    $name = get_bloginfo('name');
    return '<a class="network-text-site-title" href="' . esc_url(home_url('/')) . '" rel="home">' . esc_html($name) . '</a>';
}, 999);

add_action('wp_head', function () {
    echo '<style id="network-text-title-only-css">
    header .custom-logo,header .custom-logo-link img,header .site-logo img,
    .site-header .custom-logo,.site-header .custom-logo-link img,.site-header .site-logo img,
    .header-main .custom-logo,.header-main .site-logo img{display:none!important}
    .network-text-site-title{display:inline-block!important;color:inherit!important;text-decoration:none!important;font:700 clamp(22px,3vw,38px)/1.15 Arial,sans-serif!important;letter-spacing:-.02em!important;padding:10px 0!important}
    </style>';
}, 99);

add_action('wp_footer', function () {
    echo '<script id="network-text-title-only-js">document.addEventListener("DOMContentLoaded",function(){document.querySelectorAll("header .site-logo,.site-header .site-logo,.header-main .site-logo").forEach(function(box){if(!box.querySelector(".network-text-site-title")&&!box.textContent.trim()){var a=document.createElement("a");a.className="network-text-site-title";a.href="' . esc_url(home_url('/')) . '";a.textContent=' . wp_json_encode(get_bloginfo('name')) . ';box.appendChild(a)}})});</script>';
}, 99);
