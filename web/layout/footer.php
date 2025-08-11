<?php
declare(strict_types=1);
?>
<style>
.footer-wrapper {
  background: linear-gradient(180deg, var(--bs-body-bg) 0%, var(--bs-tertiary-bg) 100%);
  box-shadow: 0 -4px 12px rgba(0,0,0,.05);
  border-top: 1px solid var(--bs-border-color);
}
[data-bs-theme="dark"] .footer-wrapper {
  background: linear-gradient(180deg, #1a1d21 0%, #0f1114 100%);
  box-shadow: 0 -4px 12px rgba(0,0,0,.25);
}

.footer-links a,
.footer-meta a {
  color: var(--bs-secondary-color);
  text-decoration: none;
  transition: color .2s ease, opacity .2s ease, text-decoration-color .2s ease;
}
.footer-links a:hover,
.footer-meta a:hover {
  color: var(--bs-primary);
  text-decoration: underline;
  text-decoration-color: var(--bs-primary);
}

.social-row {
  display: flex;
  align-items: center;
  gap: .6rem;
  flex-wrap: wrap;
}
.social-chip {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  padding: .4rem .7rem;
  border-radius: 999px;
  border: 1px solid var(--bs-border-color);
  background: var(--bs-body-bg);
  color: var(--bs-body-color);
  text-decoration: none;
  font-size: .9rem;
  transition: transform .12s ease, border-color .2s ease, color .2s ease;
}
.social-chip:hover {
  transform: translateY(-1px);
  border-color: var(--bs-primary);
  color: var(--bs-primary);
}
.social-chip i { font-size: 1rem; }

.badge-session {
  font-weight: 600;
  letter-spacing: .02em;
}

.count-mini {
  display: inline-flex;
  align-items: baseline;
  gap: .35rem;
  padding: .25rem .55rem;
  border: 1px solid var(--bs-border-color);
  border-radius: 8px;
  background: var(--bs-body-bg);
  font-variant-numeric: tabular-nums;
}
</style>

<footer class="footer-wrapper mt-5 pt-4">
  <div class="container">

    <div class="row gy-4 pt-3">

      <!-- About -->
      <div class="col-12 col-md-5">
        <h6 class="fw-semibold mb-3"><i class="bi bi-info-circle me-1"></i>About</h6>
        <p class="small smallmuted mb-2">
          Automated research & trading for micro-caps. Live equity and positions update daily via the trading engine.
        </p>
        <ul class="small smallmuted mb-0 list-unstyled">
          <li><i class="bi bi-shield-lock me-1"></i>For informational purposes only</li>
          <li><i class="bi bi-graph-up-arrow me-1"></i>No investment advice</li>
        </ul>
      </div>

      <!-- Downloads -->
      <div class="col-12 col-md-4">
        <h6 class="fw-semibold mb-3"><i class="bi bi-download me-1"></i>Data & Downloads</h6>
        <ul class="list-unstyled footer-links small">
          <li>
            <?php if (!empty($download_equity)): ?>
              <a href="<?= htmlspecialchars($download_equity) ?>" download>Equity chart</a>
            <?php else: ?>
              <span class="text-body-secondary">Equity chart (n/a)</span>
            <?php endif; ?>
          </li>
          <li>
            <?php if (!empty($download_pnl)): ?>
              <a href="<?= htmlspecialchars($download_pnl) ?>" download>P/L chart</a>
            <?php else: ?>
              <span class="text-body-secondary">P/L chart (n/a)</span>
            <?php endif; ?>
          </li>
          <li>
            <?php if (!empty($download_positions)): ?>
              <a href="<?= htmlspecialchars($download_positions) ?>" download>Positions CSV</a>
            <?php else: ?>
              <span class="text-body-secondary">Positions CSV (n/a)</span>
            <?php endif; ?>
          </li>
          <li>
            <?php if (!empty($download_trades)): ?>
              <a href="<?= htmlspecialchars($download_trades) ?>" download>Trades CSV</a>
            <?php else: ?>
              <span class="text-body-secondary">Trades CSV (n/a)</span>
            <?php endif; ?>
          </li>
        </ul>
      </div>

      <!-- Session -->
      <div class="col-12 col-md-3">
        <h6 class="fw-semibold mb-3"><i class="bi bi-clock-history me-1"></i>Session</h6>
        <div class="small">
          <div class="mb-1">
            <span class="badge badge-session <?= $statusClass ?>"><?= htmlspecialchars($statusText) ?></span>
          </div>
          <div class="smallmuted"><?= htmlspecialchars($nextEventLabel) ?>:</div>
          <div class="count-mini mt-1">
            <span id="footerCountdown">--:--:--</span>
          </div>
            <?php
            $dtFooter = new DateTime($as_of, new DateTimeZone('UTC'));
            $dtFooter->setTimezone(new DateTimeZone('Europe/Amsterdam'));
            ?>
            <div class="small smallmuted mt-2">
              Updated: <span id="updatedFooter"><?= htmlspecialchars($dtFooter->format('D, d M Y H:i T')) ?></span>
            </div>
        </div>
      </div>

    </div>

    <hr class="mt-4 mb-3">

    <div class="d-flex flex-wrap align-items-center justify-content-between pb-3 small smallmuted">
      <div>© <?= date('Y') ?> <a href="https://monadius.com" target="_blank" rel="noopener" class="fw-semibold">Monadius</a> — <a href="https://mauriceb.nl" target="_blank" rel="noopener" class="fw-semibold">Maurice Boendermaker</a></div>
      <div>Europe/Amsterdam</div>
    </div>
  </div>
</footer>

<script>
(function(){
  // Footer countdown (self-contained; won’t clash with header timer)
  const targetIsoFooter = <?= json_encode($nextEventIso) ?>;
  const nowIsoFooter = <?= json_encode($nowIso) ?>;
  const out = document.getElementById('footerCountdown');
  if(out && targetIsoFooter && nowIsoFooter){
    const target = new Date(targetIsoFooter).getTime();
    const serverNow = new Date(nowIsoFooter).getTime();
    let drift = Date.now() - serverNow;

    function pad(n){return n<10?'0'+n:''+n}
    function tick(){
      const now = Date.now() - drift;
      let s = Math.max(0, Math.floor((target - now)/1000));
      const d = Math.floor(s/86400); s%=86400;
      const h = Math.floor(s/3600); s%=3600;
      const m = Math.floor(s/60); s%=60;
      out.textContent = (d>0?d+'d ':'') + pad(h) + ':' + pad(m) + ':' + pad(s);
    }
    tick();
    setInterval(tick, 1000);
  }
})();
</script>
