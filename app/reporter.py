import os
import re
import ssl
import smtplib

from html import escape
from typing import Dict, List, Optional, Mapping, Tuple

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders


def _md_light_to_html(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n")
    lines = t.split("\n")
    out = []
    in_ol = False
    in_ul = False

    def close_lists():
        nonlocal in_ol, in_ul, out
        if in_ol:
            out.append("</ol>")
            in_ol = False
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def inline(s: str) -> str:
        s = escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(
            r"\[(.+?)\]\((https?://[^\s)]+)\)",
            r"<a href='\2' style='color:#2563eb;text-decoration:none'>\1</a>",
            s,
        )
        return s

    for line in lines:
        if not line.strip():
            close_lists()
            out.append("<div style='height:6px'></div>")
            continue

        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            level = min(len(m.group(1)), 3)
            size = {1: 20, 2: 18, 3: 16}[level]
            out.append(
                f"<h{level} style='margin:12px 0 6px 0;font-size:{size}px;'>{inline(m.group(2))}</h{level}>"
            )
            continue

        m = re.match(r"^\s{0,3}\d+\.\s+(.*)$", line)
        if m:
            if not in_ol:
                close_lists()
                out.append("<ol style='margin:0 0 10px 22px;padding:0'>")
                in_ol = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue

        m = re.match(r"^\s{0,3}[-*]\s+(.*)$", line)
        if m:
            if not in_ul:
                close_lists()
                out.append("<ul style='margin:0 0 10px 22px;padding:0'>")
                in_ul = True
            out.append(f"<li>{inline(m.group(1))}</li>")
            continue

        close_lists()
        out.append(f"<p style='margin:0 0 10px 0'>{inline(line)}</p>")

    close_lists()
    return "\n".join(out)


def build_report_html(
    trades_today,
    positions_df,
    thesis,
    forecast,
    *,
    equity,
    cash,
    daily_pnl,
    as_of_iso,
    vote_summary: str = "",
    inline_cid: str | None = None,
    pnl_cid: str | None = None,
    total_pl: float = 0.0,
    risk_alerts: dict | None = None,
    news_by_ticker: dict | None = None,
    top_performer: Optional[Tuple[str, float]] = None,
    worst_performer: Optional[Tuple[str, float]] = None
) -> str:
    def render_alert_list(items):
        items = items or []
        if not items:
            return "<li><span style='color:#64748b'>None</span></li>"
        return "".join(f"<li style='margin-bottom:4px'>{escape(str(x))}</li>" for x in items if x)

    trades_html = (
        "".join(
            (
                "<li>"
                f"<strong>{escape(str(t.get('Date','')))}</strong> "
                f"{escape(str(t.get('Side','')))} "
                f"{escape(str(t.get('Shares','')))} "
                f"{escape(str(t.get('Ticker','')))} "
                f"<span style='color:#666'>status={escape(str(t.get('OrderStatus','')))}</span>"
                "</li>"
            )
            for t in (trades_today or [])
        )
        or "<li>None</li>"
    )

    if positions_df is not None and not getattr(positions_df, "empty", True):
        rows = []
        for _, r in positions_df.iterrows():
            ticker = str(r.get("Ticker", ""))
            qty_raw = r.get("Shares", 0)
            try:
                qf = float(qty_raw)
                qty = str(int(qf)) if qf.is_integer() else str(qf)
            except Exception:
                qty = escape(str(qty_raw))
            val_raw = r.get("Total Value", 0)
            try:
                val = float(val_raw) if val_raw is not None else 0.0
            except Exception:
                val = 0.0
            pct = (val / equity) if equity not in (0, 0.0, None) else 0.0
            rows.append(
                "<tr>"
                f"<td style='padding:8px;border-bottom:1px solid #eee'>{escape(ticker)}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;text-align:right'>{escape(qty)}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eee;text-align:right'>${val:,.2f} "
                f"<span style='color:#64748b'>({pct:.1%})</span></td>"
                "</tr>"
            )
        pos_html = "".join(rows)
    else:
        pos_html = "<tr><td colspan='3' style='padding:8px;text-align:center;color:#666'>None</td></tr>"

    chart_html = (
        f"<img src='cid:{inline_cid}' alt='Equity Curve' style='max-width:560px;width:100%;height:auto;display:block;margin:8px auto;border-radius:12px;border:1px solid #eaeaea;background:#ffffff'/>"
        if inline_cid else ""
    )
    pnl_chart_html = (
        f"<img src='cid:{pnl_cid}' alt='PnL Curve' style='max-width:560px;width:100%;height:auto;display:block;margin:8px auto;border-radius:12px;border:1px solid #eaeaea;background:#ffffff'/>"
        if pnl_cid else ""
    )

    thesis_html = _md_light_to_html(thesis or "")
    forecast_html = _md_light_to_html(forecast or "")

    pl_color = "#16a34a" if total_pl >= 0 else "#dc2626"
    daily_color = "#16a34a" if daily_pnl >= 0 else "#dc2626"

    pos_alerts_html = render_alert_list((risk_alerts or {}).get("positions"))
    sec_alerts_html = render_alert_list((risk_alerts or {}).get("sectors"))
    has_pos = bool((risk_alerts or {}).get("positions"))
    has_sec = bool((risk_alerts or {}).get("sectors"))
    alerts_html = ""
    if has_pos or has_sec:
        alerts_html = f"""
          <h2 style="margin:18px 0 8px 0;font-size:16px;">Risk Alerts</h2>
          <div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:12px">
            <div style="flex:1;min-width:240px">
              <div style="font-size:12px;color:#64748b;margin-bottom:6px">Positions</div>
              <ul style="margin:0 0 0 18px;padding:0;font-size:14px;line-height:1.6">{pos_alerts_html}</ul>
            </div>
            <div style="flex:1;min-width:240px">
              <div style="font-size:12px;color:#64748b;margin-bottom:6px">Sectors</div>
              <ul style="margin:0 0 0 18px;padding:0;font-size:14px;line-height:1.6">{sec_alerts_html}</ul>
            </div>
          </div>
        """

    top_html = ""
    if top_performer:
        sym, pct = top_performer
        top_html = f"<br/><div style='font-size:14px'><strong>Top Performer:</strong> {escape(str(sym))} <span style='color:#16a34a'>{pct:.2%}</span></div>"
    worst_html = ""
    if worst_performer:
        sym, pct = worst_performer
        worst_html = f"<div style='font-size:14px'><strong>Worst Performer:</strong> {escape(str(sym))} <span style='color:#dc2626'>{pct:.2%}</span></div>"

    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Daily Trading Report</title>
<style>
@media only screen and (max-width: 700px) {{
  .container {{ width:100% !important; border-radius:0 !important; }}
  .pad {{ padding:16px !important; }}
  img {{ max-width:100% !important; height:auto !important; }}
}}
.details-box summary {{
  cursor: pointer;
  list-style: none;
}}
.details-box summary::-webkit-details-marker {{
  display:none;
}}
</style>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#111827;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f4f6;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellspacing="0" cellpadding="0" class="container" style="background:#ffffff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.06);overflow:hidden;">
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#0ea5e9,#2563eb);color:#fff;">
              <h1 style="margin:0 0 6px 0;font-size:22px;">Daily Trading Report</h1>
              <div style="opacity:.9;font-size:13px;">{escape(as_of_iso)}</div>
            </td>
          </tr>
          <tr>
            <td class="pad" style="padding:24px 32px">

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:18px">
                <tr>
                  <td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="font-size:12px;color:#64748b">Equity</td>
                        <td style="font-size:12px;color:#64748b">Cash</td>
                        <td style="font-size:12px;color:#64748b">Daily P/L</td>
                        <td style="font-size:12px;color:#64748b">Total P/L</td>
                      </tr>
                      <tr>
                        <td style="font-weight:600;font-size:18px;padding-top:4px">${equity:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px">${cash:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px;color:{daily_color}">${daily_pnl:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px;color:{pl_color}">${total_pl:,.2f}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              {f"<div style='font-size:12px;color:#64748b;margin:-6px 0 14px 0'>Signals: {escape(vote_summary)}</div>" if vote_summary else ""}

              <div style="gap:18px;flex-wrap:wrap;margin-bottom:6px;flex-direction:column">
                <div style="flex:1;min-width:100%">{top_html}</div>
                <div style="flex:1;min-width:100%">{worst_html}</div>
              </div>

              {"<h2 style='margin:18px 0 8px 0;font-size:16px;'>Equity Curve</h2>" + chart_html if chart_html else ""}
              {"<h2 style='margin:18px 0 8px 0;font-size:16px;'>Cumulative P/L</h2>" + pnl_chart_html if pnl_chart_html else ""}

              {alerts_html}

              <h2 style="margin:18px 0 8px 0;font-size:16px;">Trades Executed Today</h2>
              <details class="details-box" style="margin:6px 0 16px 0;padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fafafa">
                <div style="margin-top:10px">
                  <ul style="margin:8px 0 0 18px;padding:0;font-size:14px;line-height:1.6">{trades_html}</ul>
                </div>
              </details>
              
              <h2 style="margin:18px 0 8px 0;font-size:16px;">Current Positions</h2>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:12px;overflow:hidden">
                <thead>
                  <tr style="background:#f8fafc">
                    <th align="left" style="padding:10px 8px;font-size:12px;color:#64748b">Ticker</th>
                    <th align="right" style="padding:10px 8px;font-size:12px;color:#64748b">Qty</th>
                    <th align="right" style="padding:10px 8px;font-size:12px;color:#64748b">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {pos_html}
                </tbody>
              </table>

              <h2 style="margin:18px 0 8px 0;font-size:16px;">AI Thesis</h2>
              <details class="details-box" style="margin:6px 0 16px 0;padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fafafa">
                <div style="margin-top:10px;font-size:14px;line-height:1.6;color:#111827">{thesis_html}</div>
              </details>

              <details class="details-box" style="margin:6px 0 16px 0;padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fafafa">
                <div style="margin-top:10px;font-size:14px;line-height:1.6;color:#111827">{forecast_html}</div>
              </details>

            </td>
          </tr>
          <tr>
            <td style="padding:18px 32px;background:#f8fafc;border-top:1px solid #e5e7eb">
              <div style="font-size:12px;color:#64748b;text-align:center">
                Developed by <strong>Monadius – Maurice Boendermaker</strong> ·
                <a href="https://github.com/MauriceBoendermaker" style="color:#2563eb;text-decoration:none">GitHub</a> ·
                <a href="https://www.linkedin.com/in/MauriceBoendermaker" style="color:#2563eb;text-decoration:none">LinkedIn</a> ·
                <a href="mailto:maurice@monadius.com" style="color:#2563eb;text-decoration:none">maurice@monadius.com</a>
              </div>
            </td>
          </tr>
        </table>
        <div style="height:24px"></div>
      </td>
    </tr>
  </table>
</body>
</html>
"""
    return html


def _get_env(key: str, default: str = "") -> str:
    v = os.getenv(key)
    return v if v is not None else default

def _bool_env(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def send_email_html(
    subject: str,
    html: str,
    inline_images: Optional[Mapping[str, str]] = None,
    attachments: Optional[List[str]] = None,
) -> None:
    host = _get_env("EMAIL_HOST", _get_env("SMTP_HOST", "localhost"))
    port = int(_get_env("EMAIL_PORT", _get_env("SMTP_PORT", "587")))
    username = _get_env("EMAIL_USERNAME", _get_env("SMTP_USER", ""))
    password = _get_env("EMAIL_PASSWORD", _get_env("SMTP_PASS", ""))
    sender = _get_env("EMAIL_SENDER", username)
    to_raw = _get_env("EMAIL_RECIPIENTS", sender)
    to = [x.strip() for x in to_raw.split(",") if x.strip()] or [sender]
    use_ssl = _bool_env("EMAIL_USE_SSL", port == 465)
    use_tls = _bool_env("EMAIL_USE_TLS", port == 587)

    if not subject:
        subject = _get_env("EMAIL_SUBJECT", "Daily Trading Report")

    msg = MIMEMultipart("related")
    alt = MIMEMultipart("alternative")
    msg.attach(alt)

    text_fallback = "Your email client does not support HTML."
    alt.attach(MIMEText(text_fallback, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))

    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)

    if inline_images:
        for cid, path in inline_images.items():
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
            msg.attach(img)

    if attachments:
        for path in attachments:
            if not path or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(path)}"')
            msg.attach(part)

    if use_ssl:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=ctx) as server:
            if username and password:
                server.login(username, password)
            server.sendmail(sender, to, msg.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                ctx = ssl.create_default_context()
                server.starttls(context=ctx)
            if username and password:
                server.login(username, password)
            server.sendmail(sender, to, msg.as_string())


def dispatch_report(report_text: str, settings: dict):
    return
