import os
import smtplib
import ssl
import re
from html import escape

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import List, Dict
from datetime import datetime, timezone
import pandas as pd


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
        s = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r"<a href='\2' style='color:#2563eb;text-decoration:none'>\1</a>", s)
        return s

    for line in lines:
        if not line.strip():
            close_lists()
            out.append("<div style='height:6px'></div>")
            continue

        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*)$", line)
        if m:
            close_lists()
            level = min(len(m.group(1)), 3)  # cap at h3 for email
            size = {1: 20, 2: 18, 3: 16}[level]
            out.append(f"<h{level} style='margin:12px 0 6px 0;font-size:{size}px;'>{inline(m.group(2))}</h{level}>")
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
    total_pl: float = 0.0
) -> str:
    trades_html = "".join([
        f"<li><strong>{escape(t.get('Date',''))}</strong> {escape(str(t.get('Side','')))} {escape(str(t.get('Shares','')))} {escape(str(t.get('Ticker','')))} <span style='color:#666'>status={escape(str(t.get('OrderStatus','')))}</span></li>"
        for t in (trades_today or [])
    ]) or "<li>None</li>"

    pos_html = ""
    if positions_df is not None and not positions_df.empty:
        rows = []
        for _, r in positions_df.iterrows():
            rows.append(f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{escape(str(r['Ticker']))}</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:right'>{escape(str(r['Shares']))}</td><td style='padding:8px;border-bottom:1px solid #eee;text-align:right'>${float(r['Total Value']):,.2f}</td></tr>")
        pos_html = "".join(rows)
    else:
        pos_html = "<tr><td colspan='3' style='padding:8px;text-align:center;color:#666'>None</td></tr>"

    chart_html = f"<img src='cid:{inline_cid}' alt='Portfolio Performance' style='width:100%;height:auto;border-radius:12px;border:1px solid #eaeaea'/>" if inline_cid else ""

    thesis_html = _md_light_to_html(thesis or "")
    forecast_html = _md_light_to_html(forecast or "")

    pl_color = "#16a34a" if total_pl >= 0 else "#dc2626"
    daily_color = "#16a34a" if daily_pnl >= 0 else "#dc2626"

    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Daily Trading Report</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#111827;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f4f6;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="680" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:16px;box-shadow:0 2px 12px rgba(0,0,0,0.06);overflow:hidden;">
          <tr>
            <td style="padding:28px 32px;background:linear-gradient(135deg,#0ea5e9,#2563eb);color:#fff;">
              <h1 style="margin:0 0 6px 0;font-size:22px;">Daily Trading Report</h1>
              <div style="opacity:.9;font-size:13px;">{as_of_iso}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:24px 32px">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:18px">
                <tr>
                  <td style="padding:14px 16px;background:#f8fafc;border:1px solid #e5e7eb;border-radius:12px">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="font-size:12px;color:#64748b">Equity</td>
                        <td style="font-size:12px;color:#64748b;text-align:center">Cash</td>
                        <td style="font-size:12px;color:#64748b;text-align:center">Daily PnL</td>
                        <td style="font-size:12px;color:#64748b;text-align:right">Total P/L</td>
                      </tr>
                      <tr>
                        <td style="font-weight:600;font-size:18px;padding-top:4px">${equity:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px;text-align:center">${cash:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px;text-align:center;color:{daily_color}">${daily_pnl:,.2f}</td>
                        <td style="font-weight:600;font-size:18px;padding-top:4px;text-align:right;color:{pl_color}">${total_pl:,.2f}</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              {f"<div style='font-size:12px;color:#64748b;margin:-6px 0 18px 0'>Signals: {escape(vote_summary)}</div>" if vote_summary else ""}

              <div style="margin:8px 0 18px 0">{chart_html}</div>

              <h2 style="margin:18px 0 8px 0;font-size:16px;">Trades Executed Today</h2>
              <ul style="margin:8px 0 18px 18px;padding:0;font-size:14px;line-height:1.6">{trades_html}</ul>

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

              <h2 style="margin:22px 0 8px 0;font-size:16px;">Updated Thesis</h2>
              <div style="font-size:14px;line-height:1.6;color:#111827">{thesis_html}</div>

              <h2 style="margin:22px 0 8px 0;font-size:16px;">Forecast For Tomorrow</h2>
              <div style="font-size:14px;line-height:1.6;color:#111827">{forecast_html}</div>
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
    return str(v).strip().lower() in {"1","true","yes","on"}

def send_email_html(subject: str, html: str, inline_image_path: str | None) -> None:
    host = _get_env("EMAIL_HOST", _get_env("SMTP_HOST", "localhost"))
    port = int(_get_env("EMAIL_PORT", _get_env("SMTP_PORT", "587")))
    username = _get_env("EMAIL_USERNAME", _get_env("SMTP_USER", ""))
    password = _get_env("EMAIL_PASSWORD", _get_env("SMTP_PASS", ""))
    sender = _get_env("EMAIL_SENDER", username)
    to_raw = _get_env("EMAIL_RECIPIENTS", sender)
    to = [x.strip() for x in to_raw.split(",") if x.strip()] or [sender]
    use_ssl = _bool_env("EMAIL_USE_SSL", port == 465)
    use_tls = _bool_env("EMAIL_USE_TLS", port == 587)

    msg = MIMEMultipart("related")
    alt = MIMEMultipart("alternative")
    msg.attach(alt)
    text_fallback = "Your email client does not support HTML."
    alt.attach(MIMEText(text_fallback, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg["Subject"] = _get_env("EMAIL_SUBJECT", "Daily Trading Report")
    msg["From"] = sender
    msg["To"] = ", ".join(to)

    if inline_image_path and os.path.exists(inline_image_path):
        with open(inline_image_path, "rb") as f:
            img = MIMEImage(f.read())
        img.add_header("Content-ID", "<chart>")
        img.add_header("Content-Disposition", "inline", filename=os.path.basename(inline_image_path))
        msg.attach(img)

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
    pass
