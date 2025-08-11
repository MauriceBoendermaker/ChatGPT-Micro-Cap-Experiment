<?php
declare(strict_types=1);

$amsTz = new DateTimeZone('Europe/Amsterdam');
$nyTz = new DateTimeZone('America/New_York');
$asOfDt = new DateTime($as_of ?: 'now');
$asOfDt->setTimezone($amsTz);
$nowAMS = new DateTime('now', $amsTz);
$nowNY = new DateTime('now', $nyTz);
$w = (int)$nowNY->format('N');
$openNY = (new DateTime($nowNY->format('Y-m-d') . ' 09:30:00', $nyTz));
$closeNY = (new DateTime($nowNY->format('Y-m-d') . ' 16:00:00', $nyTz));
$isWeekday = $w >= 1 && $w <= 5;
$isOpen = $isWeekday && $nowNY >= $openNY && $nowNY < $closeNY;

function next_business_open(DateTime $refNY, DateTimeZone $nyTz): DateTime {
    $d = clone $refNY;
    $d->setTime(9,30,0);
    if ($refNY->format('H:i:s') < '09:30:00' && (int)$refNY->format('N') >= 1 && (int)$refNY->format('N') <= 5) return $d;
    if ($refNY->format('H:i:s') >= '16:00:00') $d->modify('+1 day');
    while ((int)$d->format('N') > 5) $d->modify('+1 day');
    $d->setTimezone($nyTz);
    $d->setTime(9,30,0);
    return $d;
}

if ($isOpen) {
    $nextEventLabel = 'Closes in';
    $nextEventNY = $closeNY;
} else {
    $nextEventLabel = 'Opens in';
    $nextEventNY = next_business_open($nowNY, $nyTz);
}
$nextEventAMS = clone $nextEventNY;
$nextEventAMS->setTimezone($amsTz);
$nextEventIso = $nextEventAMS->format('c');
$nowIso = $nowAMS->format('c');
$statusText = $isOpen ? 'NASDAQ OPEN' : 'NASDAQ CLOSED';
$statusClass = $isOpen ? 'bg-success' : 'bg-secondary';
?>
<!doctype html>
<html lang="en" data-bs-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= htmlspecialchars($TITLE) ?></title>
<meta http-equiv="refresh" content="300">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
<style>
:root{--radius:8px}
body{background:linear-gradient(180deg,var(--bs-body-bg),var(--bs-body-bg))}
.navbar-gradient{background:linear-gradient(135deg,#0ea5e9,#2563eb)}
[data-bs-theme="dark"] .navbar-gradient{background:linear-gradient(135deg,#0b5ed7,#0a58ca)}
.card{border:1px solid var(--bs-border-color);border-radius:var(--radius);overflow:hidden}
.card-header{border-bottom:1px solid var(--bs-border-color);background:var(--bs-body-bg)}
.section-card .card-header{border-top-left-radius:var(--radius);border-top-right-radius:var(--radius)}
.kpi .value{font-weight:700;font-size:1.35rem}
.kpi .sub{font-size:.82rem;color:var(--bs-secondary-color)}
.badge-up{background:#ecfdf5;color:#065f46;border:1px solid #bbf7d0}
.badge-down{background:#fef2f2;color:#7f1d1d;border:1px solid #fecaca}
[data-bs-theme="dark"] .badge-up{background:#0f3b2f;color:#65f3c2;border-color:#0b2e25}
[data-bs-theme="dark"] .badge-down{background:#3b0f0f;color:#f38a8a;border-color:#3b0f0f}
.img-frame{border:1px solid var(--bs-border-color);border-radius:12px}
.table thead th{position:sticky;top:0;background:var(--bs-body-bg);z-index:1}
.table-responsive.rounded-border{border:1px solid var(--bs-border-color);border-radius:12px;overflow:hidden}
.progress{height:.7rem}
.sticky-top-nav{position:sticky;top:0;z-index:1030}
.footer-top{border-top:1px solid var(--bs-border-color)}
.footer-links a{color:var(--bs-secondary-color);text-decoration:none}
.footer-links a:hover{text-decoration:underline}
.smallmuted{color:var(--bs-secondary-color)}
.shadow-soft{box-shadow:0 10px 30px rgba(0,0,0,.06)}
.tv-wrap{border:1px solid var(--bs-border-color);border-radius:12px;overflow:hidden}
.count-pill{display:inline-flex;align-items:center;gap:.35rem;padding:.25rem .6rem;border:1px solid rgba(0,0,0,.12);border-radius:999px;background:var(--bs-body-bg)}
.nav-center { z-index: 2; }
@media (max-width: 576px){
  .nav-center .count-pill{ font-size: 0.9rem; }
}
</style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark navbar-gradient sticky-top-nav shadow-sm">
  <div class="container position-relative">
    <a class="navbar-brand fw-semibold" href="#"><i class="bi bi-graph-up-arrow me-2"></i>AI Trading Bot</a>

    <div class="nav-center position-absolute start-50 translate-middle-x text-center">
      <span class="count-pill">
        <span class="badge <?= $statusClass ?>"><?= htmlspecialchars($statusText) ?></span>
        <span class="small text-nowrap" id="sessionLabel"><?= htmlspecialchars($nextEventLabel) ?></span>
        <span class="fw-semibold text-nowrap" id="sessionCountdown">--:--:--</span>
      </span>
    </div>

    <div class="d-flex align-items-center gap-3 ms-auto">
      <span class="badge bg-light text-dark border d-none d-md-inline">
        <i class="bi bi-geo-alt me-1"></i>
        <span id="updatedBadge"><?= htmlspecialchars($asOfDt->format('D, d M Y H:i')) ?> CEST</span>
      </span>
      <div class="form-check form-switch text-white m-0">
        <input class="form-check-input" type="checkbox" role="switch" id="themeToggle">
        <label class="form-check-label" for="themeToggle"><i class="bi bi-moon-stars"></i></label>
      </div>
    </div>
  </div>
</nav>
<script>
(function(){
  const targetIso = <?= json_encode($nextEventIso) ?>;
  const nowIso = <?= json_encode($nowIso) ?>;
  const lab = document.getElementById('sessionLabel');
  const out = document.getElementById('sessionCountdown');
  const target = new Date(targetIso).getTime();
  let offset = Date.now() - new Date(nowIso).getTime();
  function pad(n){return n<10?'0'+n:''+n}
  function tick(){
    const now = Date.now() - offset;
    let s = Math.max(0, Math.floor((target - now)/1000));
    const d = Math.floor(s/86400); s%=86400;
    const h = Math.floor(s/3600); s%=3600;
    const m = Math.floor(s/60); s%=60;
    out.textContent = (d>0?d+'d ':'')+pad(h)+':'+pad(m)+':'+pad(s);
    if (target - now <= 0) { out.textContent = '00:00:00'; clearInterval(tmr); }
  }
  const tmr = setInterval(tick, 1000); tick();
})();
</script>
