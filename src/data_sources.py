from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List


@dataclass
class FundSnapshot:
    id: str
    name: str
    nav: str
    daily_return: str
    weekly_return: str
    monthly_return: str
    risk_note: str


@dataclass
class MarketSnapshot:
    name: str
    value: str
    change: str
    note: str


def fetch_fund_snapshots(funds: List[Dict[str, Any]]) -> List[FundSnapshot]:
    """
    Placeholder data source.

    Codex task:
    Replace this function with real data fetchers, for example:
    - Eastmoney / Tiantian Fund public endpoints
    - fund company official pages
    - broker or paid data API

    Keep the returned schema stable.
    """
    snapshots: List[FundSnapshot] = []
    for fund in funds:
        snapshots.append(
            FundSnapshot(
                id=fund["id"],
                name=fund["name"],
                nav="待接入数据源",
                daily_return="待接入",
                weekly_return="待接入",
                monthly_return="待接入",
                risk_note=fund.get("notes", ""),
            )
        )
    return snapshots


def fetch_market_snapshots(indicators: List[str]) -> List[MarketSnapshot]:
    """
    Placeholder market data source.

    Codex task:
    Connect this to a market data provider for Nasdaq 100, S&P 500,
    CSI 300, Hang Seng Index, USD/CNY, US 10Y Yield, and VIX.
    """
    return [
        MarketSnapshot(
            name=item,
            value="待接入数据源",
            change="待接入",
            note="等待 Codex 接入市场数据 API",
        )
        for item in indicators
    ]


def fetch_international_news_summary() -> List[str]:
    """
    Placeholder news source.

    Codex task:
    Connect to a news/search API and summarize:
    - Fed policy
    - CPI/PPI/nonfarm payrolls
    - AI and semiconductor news
    - NVIDIA, Microsoft, Apple, Amazon, Meta
    - USD/CNY and global geopolitical risks
    """
    today = date.today().isoformat()
    return [
        f"{today}：国际新闻源尚未接入。请让 Codex 在此处连接可靠新闻源。",
        "重点关注纳斯达克100QDII与易方达全球优质企业QDII对美股科技、美元汇率与全球风险偏好的敏感性。",
    ]
