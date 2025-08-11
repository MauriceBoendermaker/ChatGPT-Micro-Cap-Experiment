<?php
declare(strict_types=1);
$tv_theme = 'light';
?>
<section class="container-fluid g-0" id="markets">
  <div class="row g-0">
    <div class="col-12 g-0">
      <div class="tv-wrap" style="border-radius:0px">
        <div class="tradingview-widget-container">
          <div id="tv_tape"></div>
          <script src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
          {
            "symbols": [
              {"proName":"NASDAQ:AAPL","title":"Apple"},
              {"proName":"NASDAQ:TSLA","title":"Tesla"},
              {"proName":"NASDAQ:MSFT","title":"Microsoft"},
              {"proName":"NASDAQ:AMZN","title":"Amazon"},
              {"proName":"NASDAQ:NVDA","title":"Nvidia"},
              {"proName":"NASDAQ:SPY","title":"SPY"},
              {"proName":"NASDAQ:QQQ","title":"QQQ"}
            ],
            "showSymbolLogo": true,
            "colorTheme": "light",
            "isTransparent": false,
            "displayMode": "adaptive",
            "locale": "en"
          }
          </script>
        </div>
      </div>
    </div>
  </div>
</section>
