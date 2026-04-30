# Common Failures

## 选题过大

将题目缩小到具体公告类型、具体章节、具体字段和具体输出形式。

## Metadata 不完整

没有 `metadata.csv` 的项目很难追溯。必须补齐公告标题、日期、PDF URL 和本地路径。

## Section 未检查

抽取结果必须能回到正确章节。目录页命中、释义页命中都要记录。

## Prompt 导致幻觉

加入 null rule 和 evidence rule。要求 evidence_text 必须来自输入文本。

## 展示不可复现

准备 `demo_script.md`，用 `--limit 3` 运行小样本。

