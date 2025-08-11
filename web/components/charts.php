<?php
declare(strict_types=1);
?>
<section class="container">
  <div class="row g-4 mt-1">
    <div class="col-12 col-xl-7">
      <div class="card section-card shadow-soft">
        <div class="card-header d-flex align-items-center">
          <h6 class="mb-0"><i class="bi bi-activity me-2"></i>Equity Curve</h6>
          <div class="ms-auto">
            <?php if($download_equity): ?><a class="btn btn-sm btn-outline-primary" href="<?= htmlspecialchars($download_equity) ?>" download><i class="bi bi-download me-1"></i>Download</a><?php endif; ?>
          </div>
        </div>
        <div class="card-body">
          <?php if($equity_img): ?>
            <img class="img-fluid img-frame" src="<?= htmlspecialchars($URL_BASE . '/' . basename($equity_img)) ?>" alt="Equity Curve">
          <?php else: ?>
            <div class="text-body-secondary">No chart available yet</div>
          <?php endif; ?>
        </div>
      </div>
    </div>
    <div class="col-12 col-xl-5">
      <div class="card section-card shadow-soft mb-4">
        <div class="card-header d-flex align-items-center">
          <h6 class="mb-0"><i class="bi bi-pie-chart me-2"></i>Exposure</h6>
        </div>
        <div class="card-body">
          <div class="d-flex align-items-center mb-2">
            <div class="me-3 small smallmuted">Invested</div>
            <div class="w-100">
              <div class="progress">
                <div class="progress-bar bg-primary" role="progressbar" style="width: <?= round($exposure_pct*100,1) ?>%"></div>
              </div>
            </div>
            <div class="ms-3 small fw-semibold"><?= number_format($exposure_pct*100,1) ?>%</div>
          </div>
          <div class="row text-center mt-3">
            <div class="col"><div class="small smallmuted">Positions</div><div class="fw-semibold"><?= money($total_positions_value) ?></div></div>
            <div class="col"><div class="small smallmuted">Cash</div><div class="fw-semibold"><?= $cash!==null?money($cash):'–' ?></div></div>
            <div class="col"><div class="small smallmuted">Equity</div><div class="fw-semibold"><?= $equity!==null?money($equity):'–' ?></div></div>
          </div>
        </div>
      </div>
      <div class="card section-card shadow-soft">
        <div class="card-header d-flex align-items-center">
          <h6 class="mb-0"><i class="bi bi-graph-up me-2"></i>Cumulative P/L</h6>
          <div class="ms-auto">
            <?php if($download_pnl): ?><a class="btn btn-sm btn-outline-primary" href="<?= htmlspecialchars($download_pnl) ?>" download><i class="bi bi-download me-1"></i>Download</a><?php endif; ?>
          </div>
        </div>
        <div class="card-body">
          <?php if($pnl_img): ?>
            <img class="img-fluid img-frame" src="<?= htmlspecialchars($URL_BASE . '/' . basename($pnl_img)) ?>" alt="Cumulative P/L">
          <?php else: ?>
            <div class="text-body-secondary">No chart available yet</div>
          <?php endif; ?>
        </div>
      </div>
    </div>
  </div>
</section>
