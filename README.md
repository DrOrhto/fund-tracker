# Fund Tracker

用于追踪 5 个中风险基金项目，并结合国际时事生成每日投资简报。

## 追踪基金

1. 华夏沪深300ETF联接
2. 富国红利精选QDII
3. 纳斯达克100指数QDII
4. 兴全安泰积极养老五年FOF
5. 易方达全球优质企业QDII

## 每日报告重点

- 基金净值与涨跌幅
- 近 1 周、近 1 月表现
- 最大回撤风险
- 美股、A股、港股、汇率、VIX 指标
- 国际时事摘要
- 特别关注：纳斯达克100QDII、易方达全球优质企业QDII
- 操作建议：持有 / 加仓观察 / 减仓观察

## 本地运行

```bash
pip install -r requirements.txt
python src/generate_report.py
```

报告会输出到：

```bash
reports/YYYY-MM-DD.md
```

## GitHub Actions 自动运行

`.github/workflows/daily-report.yml` 已设置为北京时间每天 18:00 运行。GitHub Actions 使用 UTC，所以 cron 为 `0 10 * * *`。

## 给 Codex 的任务说明

你可以在 Codex 中输入：

```text
请维护这个基金追踪项目。优先改进 src/data_sources.py，让它接入可靠的数据源，获取基金净值、指数、汇率、VIX 和相关新闻，并保持 reports/YYYY-MM-DD.md 的中文日报格式清晰、稳健、可读。
```

## 注意

本项目仅用于投资记录和风险监测，不构成保证收益或买卖建议。
