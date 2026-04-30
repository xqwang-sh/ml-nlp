# Labs

本目录放 Week 12–14 的课堂示范材料。

示范项目统一使用“股东减持公告核心字段抽取”作为例子，真实访问巨潮资讯网公开公告查询接口，并下载公开 PDF。默认只抓取 5 条记录，带限速和失败日志，适合课堂演示。

## 文件

- `week12_metadata_demo.qmd`：从抓取规格到 metadata、样本下载和数据检查。
- `week13_schema_section_demo.qmd`：从解析文本到 section 定位、Pydantic schema、证据字段。
- `week14_workflow_demo.qmd`：把 Week 12/13 的步骤串成可复现 workflow。
- `cninfo_reduction_lab/`：可运行的真实巨潮减持公告示范项目。

## 运行示范项目

```bash
cd labs/cninfo_reduction_lab
python3 src/pipeline_run.py --step all
```

运行后查看：

- `data/metadata/metadata.csv`
- `outputs/reports/dataset_check_report.md`
- `outputs/reports/section_check_report.csv`
- `outputs/results/extract_results.jsonl`
- `outputs/results/records_validated.csv`
- `outputs/logs/run_log.jsonl`
