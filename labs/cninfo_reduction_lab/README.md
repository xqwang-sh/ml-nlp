# 巨潮股东减持公告真实抓取示范项目

这是 Week 12–14 的课堂 demo。它会真实访问巨潮资讯网公开公告查询接口，检索“减持计划”公告并下载公开 PDF。它不是完整答案，而是展示一个最小可复现链路：

```text
CNINFO query
  -> metadata.csv
  -> PDF download
  -> dataset check
  -> parse PDF text
  -> route section
  -> rule-based extraction
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
python3 src/pipeline_run.py --step all
```

PDF 文本解析优先使用系统中的 `pdftotext` 命令；如果没有该命令，会尝试使用 Python 包 `pypdf`。

## 单步运行

```bash
python3 src/crawl_cninfo.py
python3 src/download_pdfs.py
python3 src/check_dataset.py
python3 src/parse_docs.py
python3 src/route_sections.py
python3 src/extract_fields.py
python3 src/validate_results.py
```
