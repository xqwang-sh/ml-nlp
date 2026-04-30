# Module B Starter Code

这是金融文本智能项目的离线 starter。它不访问真实网站、不调用真实 LLM API，默认使用两条样本文本跑通：

```text
metadata.csv
  -> dataset check
  -> parsed_docs.jsonl
  -> section routing
  -> rule-based baseline extraction
  -> Pydantic validation
  -> summary report
```

真实巨潮抓取和 PDF 下载请看 `../labs/cninfo_reduction_lab/`。

## 快速开始

```bash
python3 -m pip install -r requirements.txt
python3 run.py --help
python3 run.py all
```

运行后查看：

- `outputs/reports/dataset_check_report.md`
- `outputs/reports/section_check_report.csv`
- `outputs/results/extract_results.jsonl`
- `outputs/results/records_validated.csv`
- `outputs/reports/summary_report.md`
- `outputs/logs/run_log.jsonl`

## 单步运行

```bash
python3 run.py audit
python3 run.py parse --limit 1
python3 run.py route
python3 run.py extract
python3 run.py validate
python3 run.py report
```

## LLM API 连通性检查

复制 `.env.example` 为 `.env`，填入真实 key、base URL 和 model 后运行：

```bash
python3 src/hello_llm.py --config configs/model_config.yaml
```

如果没有真实 API Key，不需要运行这一步。正式项目中仍然必须把真实 key 放在 `.env`，不要提交。

## 注意

- `data/metadata/metadata.csv` 和 `data/parsed/parsed_docs_sample.jsonl` 是离线教学样本。
- starter 的抽取是简单规则，不代表最终项目答案。
- 正式项目应替换为真实巨潮 metadata、真实 PDF 或 MinerU 解析输出。
- 不要把真实 API Key 写入代码或提交 `.env`。

