<?php
declare(strict_types=1);
?>
<section class="container my-4" id="positions">
  <div class="card section-card shadow-soft">
    <div class="card-header d-flex align-items-center">
      <h6 class="mb-0"><i class="bi bi-stack me-2"></i>Current Positions</h6>
      <div class="ms-auto d-flex gap-2">
        <input id="posSearch" class="form-control form-control-sm" style="max-width:260px" type="search" placeholder="Search ticker">
        <?php if($download_positions): ?><a class="btn btn-sm btn-outline-secondary" href="<?= htmlspecialchars($download_positions) ?>" download><i class="bi bi-filetype-csv me-1"></i>CSV</a><?php endif; ?>
      </div>
    </div>
    <div class="card-body">
      <?php if($positions): ?>
        <div class="table-responsive rounded-border">
          <table id="posTable" class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Ticker</th>
                <th class="text-end">Qty</th>
                <th class="text-end">Value</th>
                <th class="text-end">Portfolio %</th>
              </tr>
            </thead>
            <tbody>
              <?php $eq=(float)($equity??0);
              foreach($positions as $r){
                $t=(string)($r['Ticker'] ?? '');
                $q=(string)($r['Shares'] ?? '0');
                $v=(float)($r['Total Value'] ?? '0');
                $pct=$eq>0?($v/$eq*100.0):0.0;
                echo '<tr>';
                echo '<td>'.htmlspecialchars($t).'</td>';
                echo '<td class="text-end">'.htmlspecialchars($q).'</td>';
                echo '<td class="text-end">'.money($v).'</td>';
                echo '<td class="text-end">'.number_format($pct,1).'%</td>';
                echo '</tr>';
              } ?>
            </tbody>
          </table>
        </div>
      <?php else: ?>
        <div class="text-body-secondary">No positions available.</div>
      <?php endif; ?>
    </div>
    <div class="card-footer small text-end smallmuted"><?= $positions_csv ? 'Source: '.htmlspecialchars(basename($positions_csv)) : '' ?></div>
  </div>
</section>
