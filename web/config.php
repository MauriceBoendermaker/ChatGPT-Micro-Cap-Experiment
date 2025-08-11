<?php
declare(strict_types=1);

$DATA_DIR = __DIR__;
$TITLE = "AI Trading Bot | Dashboard";

function base_url(): string {
    $scheme = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') ? 'https' : 'http';
    $host = $_SERVER['HTTP_HOST'] ?? 'localhost';
    $path = rtrim(dirname($_SERVER['SCRIPT_NAME'] ?? '/'), '/\\');
    return rtrim("$scheme://$host$path", '/');
}

function latest_by_glob_multi(string $dir, array $patterns): ?string {
    $files = [];
    foreach ($patterns as $p) foreach (glob($dir . DIRECTORY_SEPARATOR . $p) ?: [] as $f) $files[] = $f;
    if (!$files) return null;
    usort($files, fn($a,$b)=>filemtime($b)<=>filemtime($a));
    return $files[0];
}

function read_csv(string $path): array {
    $rows = [];
    if (!is_file($path)) return $rows;
    if (($h = fopen($path, 'r')) !== false) {
        $header = fgetcsv($h);
        if ($header === false) { fclose($h); return $rows; }
        while (($r = fgetcsv($h)) !== false) $rows[] = array_combine($header, $r);
        fclose($h);
    }
    return $rows;
}

function money($v): string { return '$' . number_format((float)$v, 2, '.', ','); }

$URL_BASE = base_url();

$equity_img = latest_by_glob_multi($DATA_DIR, ['equity_*.png','chart_*.png']);
$pnl_img    = latest_by_glob_multi($DATA_DIR, ['pnl_*.png']);
$positions_csv = latest_by_glob_multi($DATA_DIR, ['positions_*.csv']);
$trades_csv    = latest_by_glob_multi($DATA_DIR, ['trades_*.csv']);
$meta_json = $DATA_DIR . DIRECTORY_SEPARATOR . 'meta.json';

$meta = is_file($meta_json) ? (json_decode(file_get_contents($meta_json) ?: "{}", true) ?: []) : [];
$equity = isset($meta['equity']) ? (float)$meta['equity'] : null;
$cash = isset($meta['cash']) ? (float)$meta['cash'] : null;
$daily_pnl = isset($meta['daily_pnl']) ? (float)$meta['daily_pnl'] : null;
$total_pl = isset($meta['total_pl']) ? (float)$meta['total_pl'] : null;
$as_of = $meta['as_of'] ?? date('c');

$positions = $positions_csv ? read_csv($positions_csv) : [];
$trades = $trades_csv ? read_csv($trades_csv) : [];

$total_positions_value = 0.0;
foreach ($positions as $r) $total_positions_value += (float)($r['Total Value'] ?? 0);
$exposure_pct = ($equity && $equity > 0) ? ($total_positions_value / $equity) : 0.0;

$download_positions = $positions_csv ? ($URL_BASE . '/' . basename($positions_csv)) : '';
$download_trades = $trades_csv ? ($URL_BASE . '/' . basename($trades_csv)) : '';
$download_equity = $equity_img ? ($URL_BASE . '/' . basename($equity_img)) : '';
$download_pnl = $pnl_img ? ($URL_BASE . '/' . basename($pnl_img)) : '';

$top_symbol = '';
$top_value = 0.0;
if ($positions && $equity && $equity > 0) {
    foreach ($positions as $r) {
        $v = (float)($r['Total Value'] ?? 0);
        if ($v > $top_value) { $top_value = $v; $top_symbol = (string)($r['Ticker'] ?? ''); }
    }
}
