<?php
/**
 * Koreanews365 sidebar dashboard.
 * Paste into the Code Snippets plugin without an opening PHP tag.
 */

function kn365_kbo_standings() {
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
        set_transient('kn365_kbo_standings_v1', $standings, 3 * HOUR_IN_SECONDS);
    }
    return $standings;
}

add_action('wp_footer', function () {
    if (is_admin()) {
        return;
    }
    $standings = kn365_kbo_standings();
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
        <div class="kn365-panel-head"><h2>KBO 순위</h2><span>3시간 간격</span></div>
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
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-market-overview.js" async>
          <?php echo wp_json_encode(array(
              'colorTheme' => 'light', 'dateRange' => '1D', 'showChart' => false,
              'locale' => 'kr', 'width' => '100%', 'height' => 570,
              'isTransparent' => true, 'showSymbolLogo' => true, 'showFloatingTooltip' => false,
              'tabs' => array(
                  array('title' => '한국', 'symbols' => array(
                      array('s' => 'KRX:005930', 'd' => '삼성전자'), array('s' => 'KRX:000660', 'd' => 'SK하이닉스'),
                      array('s' => 'KRX:373220', 'd' => 'LG에너지솔루션'), array('s' => 'KRX:005380', 'd' => '현대차'),
                      array('s' => 'KRX:207940', 'd' => '삼성바이오로직스'))),
                  array('title' => '미국', 'symbols' => array(
                      array('s' => 'NASDAQ:AAPL', 'd' => 'Apple'), array('s' => 'NASDAQ:MSFT', 'd' => 'Microsoft'),
                      array('s' => 'NASDAQ:AMZN', 'd' => 'Amazon'), array('s' => 'NASDAQ:TSLA', 'd' => 'Tesla'),
                      array('s' => 'NASDAQ:NVDA', 'd' => 'Nvidia'))),
                  array('title' => '코인', 'symbols' => array(
                      array('s' => 'COINBASE:BTCUSD', 'd' => 'Bitcoin / USD'),
                      array('s' => 'COINBASE:ETHUSD', 'd' => 'Ethereum / USD'),
                      array('s' => 'COINBASE:SOLUSD', 'd' => 'Solana / USD'))),
              ),
          ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); ?>
          </script>
        </div>
        <p class="kn365-disclaimer">투자 참고용 지연 정보이며 투자 권유가 아닙니다.</p>
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
      .kn365-source,.kn365-disclaimer,.kn365-muted{display:block;margin:9px 0 0;font-size:10px;color:#7a8495}.kn365-source{text-decoration:none}
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

