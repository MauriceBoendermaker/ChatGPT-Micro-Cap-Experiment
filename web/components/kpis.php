<?php
declare(strict_types=1);
?>
<section class="container my-4" id="overview">
  <div class="row g-3">
    <div class="col-12 col-lg-3">
      <div class="card kpi shadow-soft">
        <div class="card-body">
          <div class="smallmuted">Equity</div>
          <div class="value"><?= $equity!==null?money($equity):'–' ?></div>
          <div class="sub">Total account value</div>
        </div>
      </div>
    </div>
    <div class="col-12 col-lg-3">
      <div class="card kpi shadow-soft">
        <div class="card-body">
          <div class="smallmuted">Cash</div>
          <div class="value"><?= $cash!==null?money($cash):'–' ?></div>
          <div class="sub">Available to deploy</div>
        </div>
      </div>
    </div>
    <div class="col-12 col-lg-3">
      <div class="card kpi shadow-soft">
        <div class="card-body">
          <div class="smallmuted">Daily P/L</div>
          <div class="value">
            <?php if($daily_pnl!==null): ?>
              <span class="badge <?= $daily_pnl>=0?'badge-up':'badge-down' ?>"><i class="bi bi-<?= $daily_pnl>=0?'arrow-up-right':'arrow-down-right' ?> me-1"></i><?= money($daily_pnl) ?></span>
            <?php else: ?>–<?php endif; ?>
          </div>
          <div class="sub">Since today’s baseline</div>
        </div>
      </div>
    </div>
    <div class="col-12 col-lg-3">
      <div class="card kpi shadow-soft">
        <div class="card-body">
          <div class="smallmuted">Total P/L</div>
          <div class="value">
            <?php if($total_pl!==null): ?>
              <span class="badge <?= $total_pl>=0?'badge-up':'badge-down' ?>"><i class="bi bi-<?= $total_pl>=0?'arrow-up-right':'arrow-down-right' ?> me-1"></i><?= money($total_pl) ?></span>
            <?php else: ?>–<?php endif; ?>
          </div>
          <div class="sub">From inception snapshot</div>
        </div>
      </div>
    </div>
  </div>
</section>
