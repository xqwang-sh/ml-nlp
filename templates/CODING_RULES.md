# Coding Rules

## 项目边界

- 主数据必须来自巨潮资讯网公开公告。
- 不绕过登录、验证码或访问限制。
- 不修改原始 PDF。

## 文件与输出

- 配置放在 `configs/`。
- 原始数据放在 `data/`。
- 代码放在 `src/`。
- 运行日志放在 `outputs/logs/`。
- 结果放在 `outputs/results/`。
- 报告放在 `outputs/reports/`。

## 安全

- 真实 API Key 只能放在 `.env`。
- `.env` 不得提交。
- `.env.example` 只能写占位符。

## 验收

- 修改后说明运行命令。
- 批处理失败必须记录错误。
- 抽取结果必须能追溯到原文证据。

