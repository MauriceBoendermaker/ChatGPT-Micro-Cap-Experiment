<?php
declare(strict_types=1);
?>
<section class="container my-4" id="trades">
  <div class="card section-card shadow-soft">
    <div class="card-header d-flex align-items-center">
      <h6 class="mb-0"><i class="bi bi-arrow-left-right me-2"></i>Recent Trades</h6>
      <div class="ms-auto d-flex gap-2">
        <input id="trdSearch" class="form-control form-control-sm" style="max-width:260px" type="search" placeholder="Search ticker/side">
        <?php if($download_trades): ?><a class="btn btn-sm btn-outline-secondary" href="<?= htmlspecialchars($download_trades) ?>" download><i class="bi bi-filetype-csv me-1"></i>CSV</a><?php endif; ?>
      </div>
    </div>
    <div class="card-body">
      <?php if($trades): ?>
        <div class="table-responsive rounded-border" style="max-height:420px">
          <table id="trdTable" class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Date</th>
                <th>Ticker</th>
                <th>Side</th>
                <th class="text-end">Qty</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <?php foreach($trades as $t){
                $d=(string)($t['Date'] ?? '');
                $sym=(string)($t['Ticker'] ?? '');
                $side=(string)($t['Side'] ?? '');
                $qty=(string)($t['Shares'] ?? '');
                $st=(string)($t['OrderStatus'] ?? '');
                echo '<tr>';
                echo '<td>'.htmlspecialchars($d).'</td>';
                echo '<td>'.htmlspecialchars($sym).'</td>';
                echo '<td>'.htmlspecialchars(ucfirst(strtolower($side))).'</td>';
                echo '<td class="text-end">'.htmlspecialchars($qty).'</td>';
                echo '<td>'.htmlspecialchars($st).'</td>';
                echo '</tr>';
              } ?>
            </tbody>
          </table>
        </div>
      <?php else: ?>
        <div class="text-body-secondary">No recent trades.</div>
      <?php endif; ?>
    </div>
    <div class="card-footer small text-end smallmuted"><?= $trades_csv ? 'Source: '.htmlspecialchars(basename($trades_csv)) : '' ?></div>
  </div>
</section>
