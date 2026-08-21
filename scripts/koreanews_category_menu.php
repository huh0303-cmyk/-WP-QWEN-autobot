<?php
/** Build the Koreanews365 editorial desks and assign a clean primary menu. */

add_action('init', function () {
    $version = '2026-08-21-v2';
    if ($version === get_option('kn365_category_menu_version')) {
        return;
    }
    if (get_transient('kn365_category_menu_building')) {
        return;
    }
    set_transient('kn365_category_menu_building', 1, MINUTE_IN_SECONDS);

    $desks = array(
        array('name' => '정치', 'slug' => 'politics'),
        array('name' => '경제', 'slug' => 'economy'),
        array('name' => '사회', 'slug' => 'society'),
        array('name' => '문화', 'slug' => 'culture'),
        array('name' => '금융', 'slug' => 'finance'),
        array('name' => '부동산', 'slug' => 'real-estate'),
        array('name' => '국방', 'slug' => 'military'),
        array('name' => 'Art', 'slug' => 'art'),
        array('name' => '스포츠', 'slug' => 'sports'),
        array('name' => '글로벌', 'slug' => 'world'),
    );

    $term_ids = array();
    foreach ($desks as $desk) {
        $term = get_term_by('slug', $desk['slug'], 'category');
        if ($term) {
            if ($term->name !== $desk['name']) {
                wp_update_term($term->term_id, 'category', array('name' => $desk['name']));
            }
            $term_ids[$desk['slug']] = (int) $term->term_id;
            continue;
        }
        $created = wp_insert_term($desk['name'], 'category', array('slug' => $desk['slug']));
        if (!is_wp_error($created)) {
            $term_ids[$desk['slug']] = (int) $created['term_id'];
        }
    }

    if (count($term_ids) !== count($desks)) {
        delete_transient('kn365_category_menu_building');
        return;
    }

    $menu = wp_get_nav_menu_object('한국신문 카테고리');
    $menu_id = $menu ? (int) $menu->term_id : wp_create_nav_menu('한국신문 카테고리');
    if (is_wp_error($menu_id)) {
        delete_transient('kn365_category_menu_building');
        return;
    }

    $existing_items = wp_get_nav_menu_items($menu_id);
    if ($existing_items) {
        foreach ($existing_items as $item) {
            wp_delete_post($item->ID, true);
        }
    }

    foreach ($desks as $position => $desk) {
        wp_update_nav_menu_item($menu_id, 0, array(
            'menu-item-title' => $desk['name'],
            'menu-item-object-id' => $term_ids[$desk['slug']],
            'menu-item-object' => 'category',
            'menu-item-type' => 'taxonomy',
            'menu-item-status' => 'publish',
            'menu-item-position' => $position + 1,
        ));
    }

    $locations = get_theme_mod('nav_menu_locations', array());
    $locations['primary'] = $menu_id;
    set_theme_mod('nav_menu_locations', $locations);
    update_option('kn365_category_menu_version', $version, false);
    delete_transient('kn365_category_menu_building');
}, 30);

add_action('wp_head', function () {
    ?>
    <style id="kn365-category-menu-style">
      .mg-headwidget .navbar-wp .navbar-nav>li>a{padding-left:13px!important;padding-right:13px!important;white-space:nowrap}
      @media(min-width:992px) and (max-width:1280px){.mg-headwidget .navbar-wp .navbar-nav>li>a{font-size:12px!important;padding-left:8px!important;padding-right:8px!important}}
    </style>
    <?php
}, 30);
