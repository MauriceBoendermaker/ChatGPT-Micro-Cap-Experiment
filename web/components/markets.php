<?php
declare(strict_types=1);
$tv_theme = 'light';
?>
<section class="container my-4" id="markets">
  <div class="row g-4">
    <div class="col-12">
      <div class="card section-card shadow-soft">
        <div class="card-header d-flex align-items-center">
          <h6 class="mb-0"><i class="bi bi-aspect-ratio me-2"></i><?= $top_symbol ? "Live Chart: " . htmlspecialchars($top_symbol) : "Live Chart" ?></h6>
        </div>
        <div class="card-body">
          <div class="tv-wrap">
            <div id="tv_chart" style="height:520px"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
<script src="https://s3.tradingview.com/tv.js"></script>
<script src="https://s3.tradingview.com/tv.js"></script>
<script>
(function(){
  const symbol = <?= json_encode($top_symbol ?: "NASDAQ:SPY") ?>;

  function currentTheme(){
    return (document.documentElement.getAttribute('data-bs-theme') === 'dark') ? 'dark' : 'light';
  }

  // Safely replace the chart container to kill any prior instance
  function resetContainer(){
    const old = document.getElementById('tv_chart');
    if(!old) return;
    const fresh = old.cloneNode(false); // empty clone
    old.parentNode.replaceChild(fresh, old);
    return fresh;
  }

  function initChart(){
    const container = resetContainer() || document.getElementById('tv_chart');
    if (!container || typeof TradingView === 'undefined' || !TradingView.widget) return;

    // Create widget
    new TradingView.widget({
      width: "100%",
      height: 520,
      symbol: symbol,
      interval: "D",
      timezone: "Etc/UTC",
      theme: currentTheme(),
      style: "1",
      locale: "en",
      allow_symbol_change: true,
      container_id: container.id
    });
  }

  // Initialize once, after tv.js is ready
  if (typeof TradingView === 'undefined') {
    const ready = setInterval(()=>{
      if (typeof TradingView !== 'undefined' && TradingView.widget) {
        clearInterval(ready);
        initChart();
      }
    }, 50);
  } else {
    initChart();
  }

  // Re-init only on real theme changes
  window.addEventListener('theme-changed', initChart);
})();
</script>
</section>
