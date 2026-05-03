# 巨潮股东减持公告真实抓取示范项目

这是 Week 12–14 的课堂 demo。它会真实访问巨潮资讯网公开公告查询接口，检索“减持计划”公告并下载公开 PDF。它不是完整答案，而是展示一个最小可复现链路：

```text
CNINFO query
  -> metadata.csv
  -> PDF download
  -> dataset check
  -> MinerU PDF-to-Markdown
  -> route section
  -> rule-based or SiliconFlow LLM extraction
  -> Pydantic validation
  -> workflow log
```

## 合规与课堂控制

- 只访问公开公告查询接口和公开 PDF 地址。
- 不使用登录态，不绕过验证码或访问限制。
- 默认只抓取 5 条记录。
- 请求之间默认 sleep 1.2 秒。
- 所有失败写入日志。

## 运行

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
# 正式项目在 .env 中填写 MINERU_API_KEY；如果使用 LLM 抽取，也填写 LLM_*。
python3 src/pipeline_run.py --step all
```

PDF 解析步骤必须使用 MinerU API，把 PDF 转成 `data/parsed/markdown/*.md`，再写入统一的 `data/parsed/parsed_docs.jsonl`。没有真实 `MINERU_API_KEY`、MinerU 返回失败、或解析结果为空时，脚本会直接退出。

字段抽取默认使用规则 baseline：

```bash
python3 src/extract_fields.py --method rule
```

如果使用硅基流动 API，在 `.env` 中设置 `LLM_BASE_URL=https://api.siliconflow.cn/v1`、`LLM_MODEL` 和 `LLM_API_KEY`，再运行：

```bash
python3 src/extract_fields.py --method llm
```

## 单步运行

```bash
python3 src/crawl_cninfo.py
python3 src/download_pdfs.py
python3 src/check_dataset.py
python3 src/parse_docs.py
python3 src/route_sections.py
python3 src/extract_fields.py --method rule
python3 src/validate_results.py
```
