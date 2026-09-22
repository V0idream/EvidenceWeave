# EvidenceWeave V1 验收记录

验收日期：2026-09-21。环境：Windows，Python 3.12.10，Node 22.23.1，NVIDIA GeForce RTX 5070 Ti Laptop GPU（12 GB），Ollama 0.34.1，qwen3:14b。

## 自动化与构建

- 后端：`35 passed`。覆盖文本、空、多页、无文本层和 OCR fallback；页码与多块引文定位；合法、非法、缺字段、多 Fact、否定事实；金额/时间规范化；客观记录宽时间窗候选配对；四类关系 schema；客观记录差异提升为潜在矛盾；来源链；案件隔离；人工复核；人物合并；本机地址限制。
- 前端：TypeScript 与 Vite production build 成功。PDF.js worker、字体、CMap 和 wasm 均进入本地构建，无 CDN。
- 测试仅有 FastAPI/Starlette TestClient 上游弃用警告，不影响运行结果。

## 真实模型端到端

使用本地 qwen3:14b 完整执行：17 份合成 PDF → PyMuPDF 分页/块 → Atomic Fact → 规则候选 → 本地关系核验 → SQLite → API / UI。

| 项目 | 结果 |
|---|---:|
| PDF 成功导入 | 17 / 17（100%） |
| 原子事实 | 34 |
| 候选关系 | 94 |
| 固定人工标注关系对 | 20 |
| 矛盾 precision | 90.91%（10 TP / 1 FP） |
| 矛盾 recall | 100%（10 TP / 0 FN） |
| 来源引文定位准确率 | 100%（当前 34 条事实） |
| 人物 precision / recall | 100% / 100%（当前合成集） |
| 四类关系对准确率 | 95%（19 / 20） |

完整逐项结果在 `benchmark/last_report.json`。基线修正前结果保存在 `benchmark/baseline_report.json`：矛盾 precision 88.89%、recall 80%、来源定位 100%。修正内容是材料可见文字驱动的保守归一化：明确写有“参与…商议”时将事件类别归一为商议；“不能确认/没有注意到…是否”归一为 uncertain；模型原始字段及修正记录在 `extraction_metadata.grounded_corrections`。

该指标只描述 20 对固定、完全虚构的合成关系，不能外推到真实案件。没有用标准答案生成模型输出；模型结果写入数据库后再与 `gold_labels.json` 比较。未抽取到的标注事实计为漏报。

## 界面实机核验

- 创建案件、打开案件、选择目标被告、17 份文档列表及人物列表可用。
- Local Mode 真实显示 `qwen3:14b`、PyMuPDF、SQLite、MinerU unavailable、External AI Disabled。
- PDF.js 中文页面可渲染；页码从 1 跳到 2 正常。
- 分析进度从 EXTRACTING、MATCHING、VERIFYING 到 COMPLETED 可见。
- API 端到端测试覆盖关系详情、双方引用、PDF 文件、页块和 Confirm / Dismiss / Uncertain 持久化。
- 浏览器实机确认：提交复核意见后只自动打开同一待证问题、同一关系板块的下一条待复核关系；当前板块无剩余记录时关闭关系详情，不跨板块跳转。
- 一致性矩阵已移除“信息不足”；旧数据库中的该类型在启动时迁移为“实际无关”。
- 原“部分差异”板块已统一显示为“有待核实”；内部关系代码保持不变，现有案件无需迁移。

## 未完成实机边界

- MinerU 未安装，扫描 PDF 的真实 OCR 仍未实机验证；UI/后端会提示具体低质量页，文本 PDF 不受影响。
- 未用真实客户材料测试，也未进行实际案件法律语义评估。
- 未做跨进程任务队列、多人协作、云同步、移动端或外部法律数据库；这些不在 V1 范围。
- 未对真实大卷宗做长时间压力测试；分析为本机单进程后台任务。
