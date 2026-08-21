<?php
/** The Seoul Journal editorial masthead and daily data desk. */

function sj26_fetch_json($url, $timeout = 8) {
    $response = wp_remote_get($url, array('timeout' => $timeout, 'user-agent' => 'TheSeoulJournal/1.0 (+https://theseouljournal.com/)'));
    if (is_wp_error($response) || 200 !== wp_remote_retrieve_response_code($response)) return null;
    $data = json_decode(wp_remote_retrieve_body($response), true);
    return is_array($data) ? $data : null;
}

function sj26_mlb_standings() {
    $cached = get_transient('sj26_mlb_standings_v1');
    if (is_array($cached) && count($cached) === 6) return $cached;
    $season = (int) wp_date('Y');
    $data = sj26_fetch_json('https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=' . $season . '&standingsTypes=regularSeason');
    if (!$data || empty($data['records'])) return array();
    $division_names = array(201 => 'AL East', 202 => 'AL Central', 200 => 'AL West', 204 => 'NL East', 205 => 'NL Central', 203 => 'NL West');
    $order = array(201, 202, 200, 204, 205, 203);
    $divisions = array();
    foreach ($data['records'] as $record) {
        $id = (int) ($record['division']['id'] ?? 0);
        if (!isset($division_names[$id])) continue;
        $teams = array();
        foreach (($record['teamRecords'] ?? array()) as $team) {
            $teams[] = array(
                'name' => $team['team']['name'] ?? '',
                'wins' => (int) ($team['wins'] ?? 0),
                'losses' => (int) ($team['losses'] ?? 0),
                'pct' => $team['winningPercentage'] ?? '.000',
            );
        }
        $divisions[$id] = array('name' => $division_names[$id], 'teams' => $teams);
    }
    $result = array();
    foreach ($order as $id) if (isset($divisions[$id])) $result[] = $divisions[$id];
    if (count($result) === 6) set_transient('sj26_mlb_standings_v1', $result, DAY_IN_SECONDS);
    return $result;
}

function sj26_market_quotes() {
    $cached = get_transient('sj26_market_quotes_v1');
    if (is_array($cached) && count($cached) === 8) return $cached;
    $symbols = array(
        array('symbol' => 'AAPL', 'name' => 'Apple', 'group' => 'stock'),
        array('symbol' => 'NVDA', 'name' => 'Nvidia', 'group' => 'stock'),
        array('symbol' => 'TSLA', 'name' => 'Tesla', 'group' => 'stock'),
        array('symbol' => 'MSFT', 'name' => 'Microsoft', 'group' => 'stock'),
        array('symbol' => 'AMZN', 'name' => 'Amazon', 'group' => 'stock'),
        array('symbol' => 'BTC-USD', 'name' => 'Bitcoin', 'group' => 'crypto'),
        array('symbol' => 'ETH-USD', 'name' => 'Ethereum', 'group' => 'crypto'),
        array('symbol' => 'GC=F', 'name' => 'Gold / oz', 'group' => 'gold'),
    );
    $quotes = array();
    foreach ($symbols as $item) {
        $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . rawurlencode($item['symbol']) . '?range=5d&interval=1d';
        $data = sj26_fetch_json($url, 6);
        $meta = $data['chart']['result'][0]['meta'] ?? array();
        $price = (float) ($meta['regularMarketPrice'] ?? 0);
        $previous = (float) ($meta['chartPreviousClose'] ?? 0);
        if ($price <= 0 || $previous <= 0) continue;
        $quotes[] = array_merge($item, array(
            'price' => $price,
            'percent' => (($price - $previous) / $previous) * 100,
            'volume' => (int) ($meta['regularMarketVolume'] ?? 0),
        ));
    }
    if (count($quotes) === 8) set_transient('sj26_market_quotes_v1', $quotes, DAY_IN_SECONDS);
    return $quotes;
}

function sj26_fx_rates() {
    $cached = get_transient('sj26_fx_rates_v1');
    if (is_array($cached) && count($cached) === 4) return $cached;
    $data = sj26_fetch_json('https://api.frankfurter.app/latest?from=USD&to=EUR,JPY,CNY,KRW');
    $rates = $data['rates'] ?? array();
    if (count($rates) === 4) set_transient('sj26_fx_rates_v1', $rates, DAY_IN_SECONDS);
    return $rates;
}

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style('sj26-libre-caslon', 'https://fonts.googleapis.com/css2?family=Libre+Caslon+Display&family=Libre+Caslon+Text:wght@400;700&family=UnifrakturCook:wght@700&display=swap', array(), null);
}, 20);

add_action('wp_footer', function () {
    if (is_admin()) return;
    $mlb = sj26_mlb_standings();
    $quotes = sj26_market_quotes();
    $fx = sj26_fx_rates();
    $cities = array(
        array('Seoul', 'Asia/Seoul', 37.5665, 126.9780), array('New York', 'America/New_York', 40.7128, -74.0060),
        array('London', 'Europe/London', 51.5072, -0.1276), array('Los Angeles', 'America/Los_Angeles', 34.0522, -118.2437),
        array('Paris', 'Europe/Paris', 48.8566, 2.3522), array('Tokyo', 'Asia/Tokyo', 35.6762, 139.6503),
        array('Beijing', 'Asia/Shanghai', 39.9042, 116.4074),
    );
    ?>
    <aside id="sj26-dashboard" class="sj26-dashboard" aria-label="Daily data desk">
      <section class="sj26-panel sj26-mlb"><header><h2>MLB Standings</h2><span><?php echo esc_html(wp_date('M j, Y')); ?></span></header>
        <?php if ($mlb) : foreach ($mlb as $division) : ?>
          <h3><?php echo esc_html($division['name']); ?></h3><ol>
          <?php foreach ($division['teams'] as $team) : ?><li><span><?php echo esc_html($team['name']); ?></span><b><?php echo esc_html($team['wins'] . '–' . $team['losses']); ?></b><em><?php echo esc_html($team['pct']); ?></em></li><?php endforeach; ?>
          </ol>
        <?php endforeach; ?><a class="sj26-source" href="https://www.mlb.com/standings" target="_blank" rel="noopener noreferrer">Source: MLB</a><?php endif; ?>
      </section>

      <section class="sj26-panel sj26-markets"><header><h2>Market Board</h2><span><?php echo esc_html(wp_date('M j')); ?></span></header>
        <h3>Most-followed U.S. stocks</h3>
        <?php foreach ($quotes as $quote) : if ('stock' !== $quote['group']) continue; $dir = $quote['percent'] >= 0 ? 'up' : 'down'; ?>
          <div class="sj26-quote <?php echo esc_attr($dir); ?>"><strong><?php echo esc_html($quote['symbol']); ?><small><?php echo esc_html($quote['name']); ?></small></strong><span>$<?php echo esc_html(number_format($quote['price'], 2)); ?><small>Vol <?php echo esc_html(number_format($quote['volume'] / 1000000, 1)); ?>M</small></span><b><?php echo esc_html(sprintf('%+.2f%%', $quote['percent'])); ?></b></div>
        <?php endforeach; ?>
        <h3>Crypto · USD</h3>
        <?php foreach ($quotes as $quote) : if ('crypto' !== $quote['group']) continue; $dir = $quote['percent'] >= 0 ? 'up' : 'down'; ?>
          <div class="sj26-quote <?php echo esc_attr($dir); ?>"><strong><?php echo esc_html($quote['name']); ?></strong><span>$<?php echo esc_html(number_format($quote['price'], 2)); ?></span><b><?php echo esc_html(sprintf('%+.2f%%', $quote['percent'])); ?></b></div>
        <?php endforeach; ?>
        <h3>Gold · USD/oz</h3>
        <?php foreach ($quotes as $quote) : if ('gold' !== $quote['group']) continue; $dir = $quote['percent'] >= 0 ? 'up' : 'down'; ?>
          <div class="sj26-quote <?php echo esc_attr($dir); ?>"><strong>Gold</strong><span>$<?php echo esc_html(number_format($quote['price'], 2)); ?></span><b><?php echo esc_html(sprintf('%+.2f%%', $quote['percent'])); ?></b></div>
        <?php endforeach; ?><a class="sj26-source" href="https://finance.yahoo.com/" target="_blank" rel="noopener noreferrer">Daily prices: Yahoo Finance</a>
      </section>

      <section class="sj26-panel sj26-fx"><header><h2>FX · 1 USD</h2><span>Daily</span></header>
        <?php $labels = array('EUR' => 'Euro', 'JPY' => 'Japanese yen', 'CNY' => 'Chinese yuan', 'KRW' => 'Korean won'); foreach ($labels as $code => $label) : ?>
          <div><strong><?php echo esc_html($code); ?><small><?php echo esc_html($label); ?></small></strong><span><?php echo esc_html(isset($fx[$code]) ? number_format((float) $fx[$code], 'EUR' === $code ? 4 : 2) : '—'); ?></span></div>
        <?php endforeach; ?><a class="sj26-source" href="https://frankfurter.app/" target="_blank" rel="noopener noreferrer">Reference rates: Frankfurter</a>
      </section>

      <section class="sj26-panel sj26-world"><header><h2>World Clock & Weather</h2><span id="sj26-weather-status">Now</span></header><ul>
        <?php foreach ($cities as $i => $city) : ?><li data-i="<?php echo esc_attr($i); ?>" data-zone="<?php echo esc_attr($city[1]); ?>"><strong><?php echo esc_html($city[0]); ?></strong><time>--:--</time><span class="temp">--°</span></li><?php endforeach; ?>
      </ul><a class="sj26-source" href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Weather: Open-Meteo</a></section>
    </aside>
    <style id="sj26-newsroom-style">
      :root{--sj-ink:#111;--sj-rule:#c9c5bc;--sj-paper:#fff;--sj-muted:#6b6b67}
      .newsroom-wrap{background:#fff!important;color:var(--sj-ink)!important}.news-mast{background:#fff!important;border-top:1px solid var(--sj-ink)!important;border-bottom:4px double var(--sj-ink)!important}.news-brand{font-family:"UnifrakturCook","Libre Caslon Display",Georgia,serif!important;font-size:clamp(58px,8vw,104px)!important;font-weight:700!important;line-height:1!important;letter-spacing:-.025em!important;color:#050505!important}.news-tag,.news-topline,.news-nav{font-family:"Libre Caslon Text",Georgia,serif!important}.news-nav{border-top:1px solid var(--sj-rule)!important;padding-top:11px!important}
      .newsroom-wrap h2,.newsroom-wrap h3,.newsroom-wrap .wp-block-post-title{font-family:"Libre Caslon Text",Georgia,serif!important}.sj26-layout{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:30px;align-items:start;padding:0 28px 35px}.sj26-main>.breaking{margin-left:0!important;margin-right:0!important}.sj26-dashboard{display:grid;gap:16px;position:sticky;top:16px;font-family:Arial,sans-serif}.sj26-panel{background:var(--sj-paper);border:1px solid #deddd8;padding:14px;box-shadow:0 4px 16px rgba(0,0,0,.045)}.sj26-panel header{display:flex;align-items:end;justify-content:space-between;border-bottom:2px solid var(--sj-ink);padding-bottom:7px;margin-bottom:9px}.sj26-panel h2{margin:0!important;font:700 20px "Libre Caslon Text",Georgia,serif!important}.sj26-panel header span,.sj26-source{font-size:10px;color:var(--sj-muted)}.sj26-panel h3{margin:12px 0 5px!important;padding-bottom:3px;border-bottom:1px solid #e4e2dc;font:700 12px Arial,sans-serif!important;text-transform:uppercase;letter-spacing:.08em}.sj26-mlb ol{margin:0;padding:0;list-style:none}.sj26-mlb li{display:grid;grid-template-columns:1fr 45px 38px;gap:5px;padding:4px 2px;border-bottom:1px solid #efeee9;font-size:11px}.sj26-mlb li b,.sj26-mlb li em{text-align:right;font-style:normal;font-variant-numeric:tabular-nums}.sj26-quote{display:grid;grid-template-columns:minmax(90px,1fr) 83px 55px;gap:6px;align-items:center;padding:8px 2px;border-bottom:1px solid #ecebe6;font-size:11px}.sj26-quote strong small,.sj26-quote span small,.sj26-fx strong small{display:block;color:var(--sj-muted);font-size:9px;font-weight:400}.sj26-quote span,.sj26-quote b{text-align:right;font-variant-numeric:tabular-nums}.sj26-quote.up b{color:#18743c}.sj26-quote.down b{color:#b3261e}.sj26-fx>div{display:flex;justify-content:space-between;padding:8px 2px;border-bottom:1px solid #ecebe6;font-size:12px}.sj26-fx>div>span{font-weight:700;font-variant-numeric:tabular-nums}.sj26-world ul{list-style:none;margin:0;padding:0}.sj26-world li{display:grid;grid-template-columns:1fr 52px 38px;gap:5px;padding:7px 2px;border-bottom:1px solid #ecebe6;font-size:11px}.sj26-world time,.sj26-world .temp{text-align:right;font-variant-numeric:tabular-nums}.sj26-world .temp{font-weight:700}.sj26-source{display:block;margin-top:8px;text-decoration:none}
      @media(max-width:920px){.sj26-layout{grid-template-columns:1fr;padding:0 16px 25px}.sj26-dashboard{position:static}.news-brand{font-size:48px!important}}
    </style>
    <script id="sj26-newsroom-script">
      document.addEventListener('DOMContentLoaded',()=>{
        const wrap=document.querySelector('.newsroom-wrap'),dash=document.getElementById('sj26-dashboard'); if(!wrap||!dash)return;
        const children=[...wrap.children].filter(el=>!el.classList.contains('news-mast')&&!el.classList.contains('sj26-layout'));
        const layout=document.createElement('div'),main=document.createElement('main'); layout.className='sj26-layout';main.className='sj26-main';children.forEach(el=>main.appendChild(el));layout.append(main,dash);wrap.appendChild(layout);
        const cities=<?php echo wp_json_encode($cities, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
        const tick=()=>document.querySelectorAll('#sj26-dashboard [data-zone]').forEach(el=>el.querySelector('time').textContent=new Intl.DateTimeFormat('en-US',{timeZone:el.dataset.zone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date()));tick();setInterval(tick,30000);
        fetch('https://api.open-meteo.com/v1/forecast?latitude='+cities.map(c=>c[2]).join(',')+'&longitude='+cities.map(c=>c[3]).join(',')+'&current=temperature_2m&timezone=auto').then(r=>r.json()).then(data=>{(Array.isArray(data)?data:[data]).forEach((r,i)=>{const e=document.querySelector('#sj26-dashboard [data-i="'+i+'"] .temp');if(e&&r.current)e.textContent=Math.round(r.current.temperature_2m)+'°';});}).catch(()=>{});
      });
    </script>
    <?php
}, 40);
