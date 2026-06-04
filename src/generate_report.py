from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml

from data_sources import (
    fetch_fund_snapshots,
    fetch_international_news_summary,
    fetch_market_snapshots,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"
REPORT_DIR = ROOT / "reports"


def load_config() -> Dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def classify_action(fund_id: str, risk_note: str) -> str:
    if "nasdaq" in fund_id or "global" in fund_id:
        return "持有，重点观察海外科技股、美元汇率与美联储政策。"
    if "fof" in fund_id:
        return "持有，作为组合稳定器。"
    return "持有，等待更多净值与市场数据确认。"


def render_report(config: Dict[str, Any]) -> str:
    now = datetime.now()
    report_date = now.strftime("%Y-%m-%d")
    funds = fetch_fund_snapshots(config["funds"])
    markets = fetch_market_snapshots(config["market_indicators"])
    news = fetch_international_news_summary()

    lines = []
    lines.append(f"# {report_date} 基金组合每日追踪报告")
    lines.append("")
    lines.append("## 一、组合概况")
    lines.append("")
    lines.append(f"- 目标期限：1 年")
    lines.append(f"- 目标收益：{config['project']['target_return_annual']:.0%}")
    lines.append(f"- 风险定位：{config['project']['risk_profile']} / 中风险")
    lines.append(f"- 单次投入单位：1000 人民币")
    lines.append("")

    lines.append("## 二、五只基金表现")
    lines.append("")
    lines.append("| 基金 | 类型 | 风险等级 | 净值 | 日涨跌 | 近1周 | 近1月 | 操作建议 |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    fund_meta = {item["id"]: item for item in config["funds"]}
    for item in funds:
        meta = fund_meta[item.id]
        lines.append(
            f"| {item.name} | {meta['category']} | {meta['risk_level']} | {item.nav} | {item.daily_return} | {item.weekly_return} | {item.monthly_return} | {classify_action(item.id, item.risk_note)} |"
        )
    lines.append("")

    lines.append("## 三、国际市场与宏观指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 变化 | 说明 |")
    lines.append("|---|---:|---:|---|")
    for m in markets:
        lines.append(f"| {m.name} | {m.value} | {m.change} | {m.note} |")
    lines.append("")

    lines.append("## 四、国际时事摘要")
    lines.append("")
    for item in news:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 五、重点基金影响分析")
    lines.append("")
    lines.append("### 纳斯达克100指数QDII")
    lines.append("")
    lines.append("- 重点观察：美联储利率预期、美国通胀、AI资本支出、NVIDIA/Microsoft/Apple 等权重股表现。")
    lines.append("- 风险判断：若纳斯达克100单周跌幅超过 5%，需要检查是否暂停加仓或降低定投节奏。")
    lines.append("- 当前建议：持有，等待真实数据源接入后给出更精细判断。")
    lines.append("")

    lines.append("### 易方达全球优质企业QDII")
    lines.append("")
    lines.append("- 重点观察：全球龙头企业财报、美元兑人民币、欧美日市场风险偏好、地缘政治风险。")
    lines.append("- 风险判断：该基金通常比单一纳斯达克100更分散，但仍受全球股市和汇率波动影响。")
    lines.append("- 当前建议：持有，作为海外权益配置的核心之一。")
    lines.append("")

    lines.append("## 六、风险规则")
    lines.append("")
    lines.append(f"- 单只基金单周回撤预警：{config['risk_rules']['single_fund_weekly_drawdown_alert']:.0%}")
    lines.append(f"- 单只基金单月回撤预警：{config['risk_rules']['single_fund_monthly_drawdown_alert']:.0%}")
    lines.append(f"- 组合止盈观察区：{config['risk_rules']['portfolio_take_profit_zone']:.0%}")
    lines.append(f"- 组合重新评估区：{config['risk_rules']['portfolio_review_zone']:.0%}")
    lines.append("")
    lines.append("---")
    lines.append("本报告由自动化脚本生成，仅用于投资记录和风险监测，不构成保证收益或买卖建议。")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    config = load_config()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(config)
    output = REPORT_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    output.write_text(report, encoding="utf-8")
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
