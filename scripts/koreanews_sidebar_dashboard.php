<?php
/**
 * Koreanews365 sidebar dashboard.
 * Paste into the Code Snippets plugin without an opening PHP tag.
 */

function kn365_kbo_standings_v6() {
    $cached = get_transient('kn365_kbo_standings_v1');
    if (is_array($cached) && count($cached) === 10) {
        return $cached;
    }

    $response = wp_remote_get(
        'https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx',
        array('timeout' => 8, 'user-agent' => 'Koreanews365/1.0 (+https://koreanews365.com/)')
    );
    if (is_wp_error($response) || 200 !== wp_remote_retrieve_response_code($response)) {
        return array();
    }

    $html = wp_remote_retrieve_body($response);
    if (!$html) {
        return array();
    }

    $previous = libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    $dom->loadHTML('<?xml encoding="utf-8" ?>' . $html);
    $xpath = new DOMXPath($dom);
    $rows = $xpath->query("//table[contains(@class,'tData')]//tbody/tr");
    $standings = array();

    foreach ($rows as $row) {
        $cells = $xpath->query('./td', $row);
        if ($cells->length < 7) {
            continue;
        }
        $rank = trim($cells->item(0)->textContent);
        $team = trim($cells->item(1)->textContent);
        if (!preg_match('/^([1-9]|10)$/', $rank) || '' === $team) {
            continue;
        }
        $standings[] = array(
            'rank' => $rank,
            'team' => $team,
            'games' => trim($cells->item(2)->textContent),
            'rate' => trim($cells->item(6)->textContent),
        );
        if (10 === count($standings)) {
            break;
        }
    }
    libxml_clear_errors();
    libxml_use_internal_errors($previous);

    if (10 === count($standings)) {
        set_transient('kn365_kbo_standings_v1', $standings, DAY_IN_SECONDS);
    }
    return $standings;
}

function kn365_korean_stock_quotes_v6() {
    $cached = get_transient('kn365_korean_stock_quotes_v6');
    if (is_array($cached) && count($cached) === 5) {
        return $cached;
    }
    $stocks = array(
        array('ticker' => '005930.KS', 'name' => '삼성전자'),
        array('ticker' => '000660.KS', 'name' => 'SK하이닉스'),
        array('ticker' => '005380.KS', 'name' => '현대차'),
        array('ticker' => '017670.KS', 'name' => 'SK텔레콤'),
        array('ticker' => '068270.KS', 'name' => '셀트리온'),
    );
    $quotes = array();
    foreach ($stocks as $stock) {
        $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . rawurlencode($stock['ticker']) . '?range=5d&interval=1d';
        $response = wp_remote_get($url, array('timeout' => 6, 'user-agent' => 'Koreanews365/1.0'));
        if (is_wp_error($response) || 200 !== wp_remote_retrieve_response_code($response)) {
            continue;
        }
        $payload = json_decode(wp_remote_retrieve_body($response), true);
        $meta = $payload['chart']['result'][0]['meta'] ?? array();
        $price = isset($meta['regularMarketPrice']) ? (float) $meta['regularMarketPrice'] : 0;
        $previous = isset($meta['chartPreviousClose']) ? (float) $meta['chartPreviousClose'] : 0;
        if ($price <= 0 || $previous <= 0) {
            continue;
        }
        $change = $price - $previous;
        $quotes[] = array(
            'name' => $stock['name'],
            'price' => $price,
            'change' => $change,
            'percent' => ($change / $previous) * 100,
        );
    }
    if (count($quotes) === 5) {
        set_transient('kn365_korean_stock_quotes_v6', $quotes, 10 * MINUTE_IN_SECONDS);
    }
    return $quotes;
}

add_action('wp_footer', function () {
    if (is_admin()) {
        return;
    }
    $standings = kn365_kbo_standings_v6();
    $korean_quotes = kn365_korean_stock_quotes_v6();
    $cities = array(
        array('서울', 'Asia/Seoul', 37.5665, 126.9780),
        array('뉴욕', 'America/New_York', 40.7128, -74.0060),
        array('런던', 'Europe/London', 51.5072, -0.1276),
        array('LA', 'America/Los_Angeles', 34.0522, -118.2437),
        array('파리', 'Europe/Paris', 48.8566, 2.3522),
        array('베른', 'Europe/Zurich', 46.9480, 7.4474),
        array('마드리드', 'Europe/Madrid', 40.4168, -3.7038),
    );
    ?>
    <aside id="kn365-dashboard" class="kn365-dashboard" aria-label="실시간 정보">
      <section class="kn365-panel kn365-kbo">
        <div class="kn365-panel-head"><h2>KBO 순위</h2><span>2026.8.21 기준</span></div>
        <?php if ($standings) : ?>
          <table><thead><tr><th>순위</th><th>팀</th><th>경기</th><th>승률</th></tr></thead><tbody>
          <?php foreach ($standings as $row) : ?>
            <tr><td><?php echo esc_html($row['rank']); ?></td><td><?php echo esc_html($row['team']); ?></td><td><?php echo esc_html($row['games']); ?></td><td><?php echo esc_html($row['rate']); ?></td></tr>
          <?php endforeach; ?>
          </tbody></table>
          <a class="kn365-source" href="https://www.koreabaseball.com/Record/TeamRank/TeamRank.aspx" target="_blank" rel="noopener noreferrer">출처: KBO 공식 기록</a>
        <?php else : ?>
          <p class="kn365-muted">현재 순위를 불러오는 중입니다.</p>
        <?php endif; ?>
      </section>

      <section class="kn365-panel kn365-market">
        <div class="kn365-panel-head"><h2>주요 시세</h2><span>지연 시세</span></div>
        <?php
        ?>
        <div class="kn365-market-group kn365-korean-quotes">
          <h3>한국 주식 · KRW</h3>
          <?php if (count($korean_quotes) === 5) : ?>
            <div class="kn365-korean-quote-head"><span>종목</span><span>현재가</span><span>등락률</span></div>
            <?php foreach ($korean_quotes as $quote) :
                $direction = $quote['change'] > 0 ? 'up' : ($quote['change'] < 0 ? 'down' : 'flat');
            ?>
              <div class="kn365-korean-quote <?php echo esc_attr($direction); ?>">
                <strong><?php echo esc_html($quote['name']); ?></strong>
                <span class="price"><?php echo esc_html(number_format($quote['price'], 0)); ?>원</span>
                <span class="change"><?php echo esc_html(sprintf('%+.2f%%', $quote['percent'])); ?></span>
              </div>
            <?php endforeach; ?>
            <a class="kn365-source" href="https://finance.yahoo.com/" target="_blank" rel="noopener noreferrer">시세: Yahoo Finance · 10분 간격</a>
          <?php else : ?>
            <p class="kn365-muted">한국 주식 시세를 불러오는 중입니다.</p>
          <?php endif; ?>
        </div>
        <?php
        $market_groups = array(
            '미국 주식 · USD' => array(
                array('s' => 'NASDAQ:AAPL', 'd' => 'Apple'),
                array('s' => 'NASDAQ:MSFT', 'd' => 'Microsoft'),
                array('s' => 'NASDAQ:AMZN', 'd' => 'Amazon'),
                array('s' => 'NASDAQ:TSLA', 'd' => 'Tesla'),
                array('s' => 'NASDAQ:NVDA', 'd' => 'Nvidia'),
            ),
            '암호화폐 · USD' => array(
                array('s' => 'COINBASE:BTCUSD', 'd' => 'Bitcoin'),
                array('s' => 'COINBASE:ETHUSD', 'd' => 'Ethereum'),
            ),
        );
        foreach ($market_groups as $group_title => $symbols) :
            $market_height = count($symbols) > 3 ? 335 : 245;
        ?>
          <div class="kn365-market-group">
            <h3><?php echo esc_html($group_title); ?></h3>
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
              <?php echo wp_json_encode(array(
                  'colorTheme' => 'light', 'dateRange' => '1D', 'showChart' => false,
                  'locale' => 'kr', 'width' => '100%', 'height' => $market_height,
                  'isTransparent' => true, 'showSymbolLogo' => true, 'showFloatingTooltip' => false,
                  'tabs' => array(array('title' => $group_title, 'symbols' => $symbols)),
              ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>
              </script>
            </div>
          </div>
        <?php endforeach; ?>
        <p class="kn365-disclaimer">투자 참고용 지연 정보이며 투자 권유가 아닙니다.</p>
      </section>

      <section class="kn365-panel kn365-gold">
        <div class="kn365-panel-head"><h2>국제 금 시세</h2><span>USD/oz · 지연 시세</span></div>
        <div class="kn365-gold-quote" aria-label="트로이온스당 국제 금 현물가와 등락률">
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-info.js" async>
          <?php echo wp_json_encode(array(
              'symbol' => 'OANDA:XAUUSD', 'width' => '100%', 'locale' => 'kr',
              'colorTheme' => 'light', 'isTransparent' => true,
          ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>
          </script>
        </div>
        <p class="kn365-disclaimer">금 현물 1트로이온스당 미국 달러 기준입니다.</p>
      </section>

      <section class="kn365-panel kn365-world">
        <div class="kn365-panel-head"><h2>세계 시각·기온</h2><span id="kn365-weather-time">갱신 중</span></div>
        <ul>
        <?php foreach ($cities as $i => $city) : ?>
          <li data-index="<?php echo esc_attr($i); ?>" data-zone="<?php echo esc_attr($city[1]); ?>">
            <strong><?php echo esc_html($city[0]); ?></strong><time>--:--</time><span class="temp">--°</span>
          </li>
        <?php endforeach; ?>
        </ul>
        <a class="kn365-source" href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">날씨: Open-Meteo</a>
      </section>
    </aside>
    <style>
      #secondary .widget {display:none!important} #secondary{display:block!important}
      .kn365-dashboard{display:grid;gap:16px;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR",sans-serif;color:#172033}
      .kn365-panel{background:#fff;border:1px solid #e4e9f1;border-radius:14px;box-shadow:0 7px 22px rgba(20,39,70,.07);padding:15px;overflow:hidden}
      .kn365-panel-head{display:flex;align-items:center;justify-content:space-between;border-bottom:2px solid #b5121b;margin:-2px 0 10px;padding:0 0 8px}
      .kn365-panel-head h2{font-size:18px!important;margin:0!important;color:#101c35}.kn365-panel-head span{font-size:11px;color:#778196}
      .kn365-kbo table{width:100%;border-collapse:collapse;font-size:12px}.kn365-kbo th,.kn365-kbo td{padding:5px 4px;border-bottom:1px solid #edf0f4;text-align:center}.kn365-kbo th:nth-child(2),.kn365-kbo td:nth-child(2){text-align:left;font-weight:700}
      .kn365-kbo tbody tr:nth-child(6) td{border-top:2px dashed #c91421;padding-top:18px}
      .kn365-kbo tbody tr:nth-child(6) td:first-child{position:relative}
      .kn365-kbo tbody tr:nth-child(6) td:first-child::before{content:"가을야구 커트라인";position:absolute;top:2px;left:0;width:240px;text-align:center;color:#c91421;font-size:10px;font-weight:800;letter-spacing:.08em}
      .kn365-source,.kn365-disclaimer,.kn365-muted{display:block;margin:9px 0 0;font-size:10px;color:#7a8495}.kn365-source{text-decoration:none}
      .kn365-market-group{margin:0 0 14px}.kn365-market-group h3{margin:0 0 5px!important;font-size:13px!important;color:#26334a;letter-spacing:.04em}
      .kn365-korean-quote-head,.kn365-korean-quote{display:grid;grid-template-columns:minmax(90px,1fr) 84px 58px;gap:7px;align-items:center}
      .kn365-korean-quote-head{padding:5px 3px;color:#8a93a2;font-size:10px}.kn365-korean-quote-head span:not(:first-child){text-align:right}
      .kn365-korean-quote{min-height:42px;padding:8px 3px;border-bottom:1px solid #edf0f4;font-size:12px}.kn365-korean-quote strong{font-size:12px;white-space:nowrap}.kn365-korean-quote .price,.kn365-korean-quote .change{text-align:right;font-variant-numeric:tabular-nums}.kn365-korean-quote .price{font-weight:700}.kn365-korean-quote.up .change{color:#d71920}.kn365-korean-quote.down .change{color:#1769d2}.kn365-korean-quote.flat .change{color:#657080}
      .kn365-gold-quote{height:116px;overflow:hidden}
      .kn365-world ul{list-style:none;margin:0;padding:0}.kn365-world li{display:grid;grid-template-columns:1fr 58px 45px;gap:6px;padding:7px 2px;border-bottom:1px solid #edf0f4;font-size:12px}.kn365-world time,.kn365-world .temp{text-align:right;font-variant-numeric:tabular-nums}.kn365-world .temp{font-weight:700;color:#b5121b}
      @media(max-width:767px){.kn365-dashboard{margin-top:18px}.kn365-panel{border-radius:12px}}
    </style>
    <script>
    (()=>{
      const dash=document.getElementById('kn365-dashboard'), side=document.getElementById('secondary');
      if(!dash||!side)return; side.innerHTML=''; side.appendChild(dash);
      const cities=<?php echo wp_json_encode($cities, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>;
      const tick=()=>document.querySelectorAll('#kn365-dashboard [data-zone]').forEach(el=>{
        el.querySelector('time').textContent=new Intl.DateTimeFormat('ko-KR',{timeZone:el.dataset.zone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date());
      }); tick(); setInterval(tick,30000);
      const lat=cities.map(c=>c[2]).join(','), lon=cities.map(c=>c[3]).join(',');
      fetch('https://api.open-meteo.com/v1/forecast?latitude='+lat+'&longitude='+lon+'&current=temperature_2m&timezone=auto')
        .then(r=>r.json()).then(data=>{const rows=Array.isArray(data)?data:[data]; rows.forEach((r,i)=>{const el=document.querySelector('#kn365-dashboard [data-index="'+i+'"] .temp');if(el&&r.current)el.textContent=Math.round(r.current.temperature_2m)+'°';}); const t=document.getElementById('kn365-weather-time');if(t)t.textContent='현재';})
        .catch(()=>{const t=document.getElementById('kn365-weather-time');if(t)t.textContent='시간 표시';});
    })();
    </script>
    <?php
}, 40);

