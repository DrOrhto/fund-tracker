from __future__ import annotations

import argparse
import hashlib
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml


EASTMONEY_NAV_URL = "https://api.fund.eastmoney.com/f10/lsjz"
EASTMONEY_HEADERS = {
    "Referer": "https://fundf10.eastmoney.com/",
    "User-Agent": "Mozilla/5.0 fund-tracker/1.0",
}
EASTMONEY_PAGE_SIZE = 20


@dataclass
class FundMetrics:
    daily_return: float
    weekly_return: float
    monthly_return: float
    max_drawdown: float
    volatility: float


@dataclass
class FundNavData:
    nav: pd.Series
    source: str
    latest_date: str


def setup_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "fund_data_errors.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not config or "funds" not in config:
        raise ValueError("config.yaml must contain a funds list")
    if len(config["funds"]) != 5:
        raise ValueError(f"Expected exactly 5 funds, got {len(config['funds'])}")
    return config


def stable_seed(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**32)


def synthetic_nav_series(seed: int, days: int = 90) -> pd.Series:
    """Generate deterministic fallback NAV data if the real fund data source fails."""
    rng = np.random.default_rng(seed)
    daily_returns = rng.normal(loc=0.00035, scale=0.012, size=days)
    nav = 1.0 * np.cumprod(1 + daily_returns)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    return pd.Series(nav, index=dates, name="nav")


def fetch_eastmoney_page(fund_code: str, page_index: int) -> dict[str, Any]:
    params = {
        "fundCode": fund_code,
        "pageIndex": page_index,
        "pageSize": EASTMONEY_PAGE_SIZE,
        "startDate": "",
        "endDate": "",
        "_": int(time.time() * 1000),
    }
    response = requests.get(
        EASTMONEY_NAV_URL,
        params=params,
        headers=EASTMONEY_HEADERS,
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("ErrCode") not in (0, None):
        raise ValueError(f"Eastmoney returned ErrCode={payload.get('ErrCode')}: {payload.get('ErrMsg')}")
    return payload


def fetch_eastmoney_nav_series(fund_code: str, days: int = 90) -> FundNavData:
    records: list[dict[str, Any]] = []
    page_index = 1
    max_pages = math.ceil(days / EASTMONEY_PAGE_SIZE) + 2

    while len(records) < days and page_index <= max_pages:
        payload = fetch_eastmoney_page(fund_code, page_index)
        page_records = payload.get("Data", {}).get("LSJZList", [])
        if not page_records:
            break
        records.extend(page_records)
        if len(page_records) < EASTMONEY_PAGE_SIZE:
            break
        page_index += 1

    if not records:
        raise ValueError("Eastmoney returned no NAV records")

    df = pd.DataFrame(records)
    if "FSRQ" not in df or "DWJZ" not in df:
        raise ValueError("Eastmoney response is missing FSRQ or DWJZ")

    df["date"] = pd.to_datetime(df["FSRQ"], errors="coerce")
    df["nav"] = pd.to_numeric(df["DWJZ"], errors="coerce")
    df = df.dropna(subset=["date", "nav"]).drop_duplicates(subset=["date"]).sort_values("date")
    if len(df) < 22:
        raise ValueError(f"Need at least 22 real NAV observations, got {len(df)}")

    df = df.tail(days)
    nav = pd.Series(df["nav"].to_numpy(), index=df["date"], name="nav")
    latest_date = df["date"].iloc[-1].strftime("%Y-%m-%d")
    return FundNavData(nav=nav, source="Eastmoney", latest_date=latest_date)


def load_fund_nav(fund: dict[str, Any]) -> FundNavData:
    fund_code = str(fund.get("fund_code", "")).strip()
    if fund_code:
        try:
            return fetch_eastmoney_nav_series(fund_code)
        except Exception as exc:
            logging.exception(
                "Failed to fetch real NAV for %s (%s), falling back to synthetic data: %s",
                fund.get("name", fund.get("id", "unknown")),
                fund_code,
                exc,
            )
    else:
        logging.error(
            "Fund %s has no fund_code configured, falling back to synthetic data",
            fund.get("name", fund.get("id", "unknown")),
        )

    nav = synthetic_nav_series(seed=stable_seed(str(fund["id"])))
    return FundNavData(nav=nav, source="synthetic_nav_series", latest_date=nav.index[-1].strftime("%Y-%m-%d"))


def compute_metrics(nav: pd.Series) -> FundMetrics:
    nav = nav.dropna().astype(float)
    if len(nav) < 22:
        raise ValueError("Need at least 22 NAV observations to compute metrics")

    returns = nav.pct_change().dropna()
    running_max = nav.cummax()
    drawdowns = nav / running_max - 1

    daily_return = returns.iloc[-1]
    weekly_return = nav.iloc[-1] / nav.iloc[-6] - 1 if len(nav) >= 6 else math.nan
    monthly_return = nav.iloc[-1] / nav.iloc[-22] - 1 if len(nav) >= 22 else math.nan
    max_drawdown = drawdowns.min()
    volatility = returns.std(ddof=1) * math.sqrt(252)

    return FundMetrics(
        daily_return=daily_return,
        weekly_return=weekly_return,
        monthly_return=monthly_return,
        max_drawdown=max_drawdown,
        volatility=volatility,
    )


def pct(value: float) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.2f}%"


def risk_label(metrics: FundMetrics) -> str:
    if metrics.max_drawdown <= -0.10 or metrics.volatility >= 0.30:
        return "高风险关注"
    if metrics.max_drawdown <= -0.05 or metrics.volatility >= 0.20:
        return "中等波动"
    return "正常"


def build_macro_section() -> str:
    topics = {
        "美联储": "重点跟踪利率路径、降息预期变化与美元流动性，对纳斯达克100QDII和全球优质企业QDII影响较大。",
        "CPI": "若通胀高于预期，可能推升美债收益率并压制成长股估值；若低于预期，则利好科技成长资产。",
        "非农就业": "就业强弱会影响降息时点预期；过热就业可能延后宽松，疲弱就业则提高避险需求。",
        "NVIDIA": "作为AI算力核心公司，其业绩、指引和供应链变化会影响AI主题与纳斯达克100表现。",
        "Microsoft": "Azure、Copilot与企业AI支出是观察AI商业化的重要窗口，影响大型科技股风险偏好。",
        "AI产业链": "关注算力芯片、云服务、数据中心、电力设备、软件应用的景气扩散与估值回撤风险。",
    }
    lines = ["## 国际时事与宏观分析", ""]
    for topic, text in topics.items():
        lines.append(f"### {topic}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def generate_report(config: dict[str, Any], output_dir: Path) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    project = config.get("project", {})
    rows: list[dict[str, str]] = []

    for fund in config["funds"]:
        try:
            nav_data = load_fund_nav(fund)
            metrics = compute_metrics(nav_data.nav)
        except Exception as exc:
            logging.exception(
                "Failed to compute metrics for %s, using synthetic fallback: %s",
                fund.get("name", fund.get("id", "unknown")),
                exc,
            )
            fallback_nav = synthetic_nav_series(seed=stable_seed(str(fund["id"])))
            nav_data = FundNavData(
                nav=fallback_nav,
                source="synthetic_nav_series",
                latest_date=fallback_nav.index[-1].strftime("%Y-%m-%d"),
            )
            metrics = compute_metrics(nav_data.nav)

        rows.append({
            "基金": fund["name"],
            "基金代码": str(fund.get("fund_code", "")),
            "类别": fund.get("category", ""),
            "风险等级": fund.get("risk_level", ""),
            "投入金额": f"{fund.get('allocation_cny', 0):,.0f} CNY",
            "最新净值": f"{nav_data.nav.iloc[-1]:.4f}",
            "净值日期": nav_data.latest_date,
            "当日涨跌幅": pct(metrics.daily_return),
            "近1周收益": pct(metrics.weekly_return),
            "近1个月收益": pct(metrics.monthly_return),
            "最大回撤": pct(metrics.max_drawdown),
            "波动率": pct(metrics.volatility),
            "数据源": nav_data.source,
            "风险状态": risk_label(metrics),
        })

    df = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{today}.md"

    lines = [
        f"# {project.get('name', 'fund-tracker')} 基金日报 - {today}",
        "",
        "## 投资组合概况",
        f"- 基础货币：{project.get('base_currency', 'CNY')}",
        f"- 目标年化收益：{project.get('target_return_annual', 0.10) * 100:.1f}%",
        f"- 风险画像：{project.get('risk_profile', 'medium')}",
        f"- 基金数量：{len(config['funds'])}",
        "",
        "## 五只基金绩效与风险指标",
        "",
        df.to_markdown(index=False),
        "",
        "## 风险监控结论",
        "",
    ]

    high_risk = df[df["风险状态"] == "高风险关注"]
    medium_risk = df[df["风险状态"] == "中等波动"]
    if not high_risk.empty:
        lines.append("- 存在高风险关注基金，建议降低单日追涨并复核QDII溢价、汇率和海外科技股估值。")
    elif not medium_risk.empty:
        lines.append("- 存在中等波动基金，建议继续观察近1周与近1个月收益变化。")
    else:
        lines.append("- 当前组合风险状态正常，继续执行每日跟踪。")

    fallback_funds = df[df["数据源"] == "synthetic_nav_series"]
    if not fallback_funds.empty:
        names = "、".join(fallback_funds["基金"].tolist())
        lines.append(f"- 以下基金真实净值读取失败，已自动使用模拟净值兜底：{names}。请查看 logs/fund_data_errors.log。")

    lines.extend([
        "",
        build_macro_section(),
        "## 明日观察重点",
        "",
        "- 纳斯达克100与大型科技股走势",
        "- 美债10年期收益率、美元指数与人民币汇率",
        "- QDII基金申购限额、溢价率与净值更新",
        "- A股、港股资金面与政策信号",
        "",
        "## 数据说明",
        "",
        "- 基金净值优先读取 Eastmoney/Tiantian Fund 历史净值接口，并基于最近净值序列计算收益、回撤和波动率。",
        "- 单只基金真实数据获取或指标计算失败时，会记录错误日志并自动 fallback 到 synthetic_nav_series，不中断整份日报生成。",
    ])

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate daily fund markdown report")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()

    setup_logging(Path("logs"))
    config = load_config(Path(args.config))
    report_path = generate_report(config, Path(args.output_dir))
    print(f"Generated report: {report_path}")


if __name__ == "__main__":
    main()
