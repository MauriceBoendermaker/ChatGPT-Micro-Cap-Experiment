from .alpaca_service import get_last_trade_price


def market_is_healthy(alpaca) -> bool:
    try:
        spy = get_last_trade_price(alpaca, "SPY")
        qqq = get_last_trade_price(alpaca, "QQQ")
        vix = get_last_trade_price(alpaca, "VIXY")  # ETF proxy for VIX

        if vix > 25:  # High fear
            return False
        if spy < 0 or qqq < 0:
            return False
        return True

    except Exception:
        return True
