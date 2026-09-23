# EvidenceWeave V1

面向刑事辩护律师的**本地证据交叉核验工作台**。围绕选定人物整理本人陈述、他人提及和相关客观材料，发现值得人工核验的支持、冲突与差异，并追溯到 PDF 页码、原文及原文块。

**No Citation, No Claim. · AI flags. Lawyers decide. · Case data stays local.**

## LexHack 演示

`demo/` 收录约 2 分 34 秒、1080p 的最终实机演示成片，以及独立字幕参考与配音稿。最终成片包含片头片尾、英文配音、BGM 和纯黑双语硬字幕，演示直接使用预先完成的分析结果，集中展示一致性矩阵、证据关系和卷宗材料回查流程。

## 开始使用

Windows：双击 `Start-EvidenceWeave.cmd`，打开 **http://127.0.0.1:8765**。

本次本机交付包含已构建前端、Python 虚拟环境、本地 Ollama 运行库及 14B / 8B 模型，另附一个已导入的虚构案件。源码 ZIP 不包含大型模型、虚拟环境、node_modules 或运行数据库。

拿到源码压缩包后的首次启动：

1. 安装 Python 3.11+；已附 `frontend/dist` 时无需 Node。修改前端时需要 Node 22+。
2. 安装 [Ollama](https://ollama.com)，运行 `ollama pull qwen3:14b`；资源较少时可用 `ollama pull qwen3:8b`。
3. 复制 `.env.example` 为 `.env`，按需修改设置。
4. 双击启动脚本。首次会创建 `.venv` 并安装 Python 依赖，后续正常运行不需要联网。

停止本启动器创建的服务：双击 `Stop-EvidenceWeave.cmd`。重新启动会把意外中断的分析标为失败，保留上次完整结果，支持重新分析。程序仅监听回环地址；这是单机工作台，不提供网络多人服务。

## 工作流程

1. 新建案件，进入「卷宗材料」，批量导入 PDF；单文件默认最大 100 MB。
2. 检查解析提示。文本页正常导入；扫描页未配置 OCR 时显示具体页码警告。
3. 核对左侧人物，编辑角色及已确认别名。相似称呼不自动合并；可选择规范人物后点击「我已核实，合并人物」。
4. 在「材料信息」中补充陈述人、材料类型、讯问或陈述日期；这与事实发生时间不同。
5. 选择目标被告，点击「开始分析」。页面轮询显示提取、标准化、匹配和核验进度。失败展示阶段与原因。
6. 在「一致性矩阵」筛选潜在矛盾、相互印证、有待核实或实际无关。事实性/客观记录的可比不一致直接进入潜在矛盾，等待人工核验。
7. 人工复核提交意见后只在同一待证问题、同一关系板块内跳到下一条待复核关系；当前板块全部复核后自动关闭详情，不会跳到潜在矛盾等其他板块。
8. 点击关系查看 Fact A / B、AI 原因、引文与来源类型。点击来源，PDF.js 跳到引用页；可靠坐标存在时高亮原文块。
9. 保存律师「确认 / 否定 / 不确定」及备注。人工状态独立于 AI 判断。
10. 「供述变化」按同一陈述人的材料日期显示引文，标出跨文档差异；日期不详时不猜顺序。

修改人物或材料信息后需要重新分析。旧完整分析在新分析失败时继续可见；成功后当前视图切到新一轮。旧轮次的事实、关系与复核保存在 SQLite，但 V1 暂未提供历史轮次切换页，复核不会自动套用到新的模型判断。

## 核心架构

`PDF → PyMuPDF / 可选本地 OCR → 页与原始块 → Statement → Atomic Fact → 规则候选匹配 → Ollama 关系核验 → 来源定位 → 人工复核`

- 前端：React、TypeScript、Vite、Tailwind CSS、PDF.js。字体、CMap、PDF worker 和 wasm 均本地提供，无 CDN。
- 后端：FastAPI、Pydantic、SQLAlchemy、SQLite、PyMuPDF。
- 模型：Ollama，默认 `qwen3:14b`；仅在默认模型未安装且备用已安装时使用 `qwen3:8b`。可通过 `.env` 修改。内存不足等推理错误直接报告，不偷偷换模型。
- 原子事实和关系均使用 JSON Schema 约束并进行 Pydantic 校验。非法 JSON 自动修复一次，再失败则分析失败。
- 引文必须是原文连续片段。仅允许空白字符差异，并还原回逐字原文。引用不合格时重试一次，再失败拒绝发布。
- 同页几何连续行可组成提取单元，仍保存所有原始块 ID。不同页、不同栏及已结束的段落不自动拼接。
- 候选规则按主体、事件类型、时间及可比较对象缩小范围；不会把全案所有事实交给模型逐对比较。
- 每一轮分析完成前不会替换当前完整结果，防止把半成品展示为完成。

## 本地运行与配置

手动运行：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
$env:PYTHONPATH = "backend"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

开发前端：

```powershell
npm --prefix frontend ci
npm --prefix frontend run dev
```

开发服务器为 127.0.0.1:5173，`/api` 代理至本地 8765。正式构建运行 `npm --prefix frontend run build`。

配置见 `.env.example`：`DATABASE_URL`、`DATA_DIR`、`OLLAMA_BASE_URL`、`OLLAMA_MODEL`、`OLLAMA_FALLBACK_MODEL`、`OLLAMA_TIMEOUT`、`OCR_PROVIDER`、`MINERU_COMMAND`、`MAX_UPLOAD_MB`。默认路径相对于项目，无开发者绝对路径。

`OLLAMA_BASE_URL` 只允许 localhost / 127.0.0.1 / ::1。Ollama 服务关闭或模型缺失时，案件、人物、PDF 导入仍可使用，分析显示安装提示。右上角 Local Mode 可点击刷新真实系统状态，不声称有网络请求计数。

## PDF 与 OCR

优先读取文本层，逐页检查字数、可打印比例、乱码比例及空页比例。低质量页才触发 OCR 接口。加密、损坏和非 PDF 文件单独报错，不影响同批其他有效文件。

MinerU 是**可选插件**，未安装不影响文本 PDF。当前适配的是传统 `mineru -p input.pdf -o output -b pipeline` CLI 及 `*_content_list.json`（`page_idx` 从 0 开始）。设置 `OCR_PROVIDER=mineru` 和 `MINERU_COMMAND`，预先按对应版本配置本地权重。调用强制 `MINERU_MODEL_SOURCE=local`，不调用远程文档服务。MinerU 4 的 `mineru-kit` CLI 不等同于此适配器，不能直接替换命令名。

本次未安装 MinerU，因此真实扫描卷宗 OCR 未做实机验收；自动化测试覆盖无 OCR 的降级和模拟 OCR 输出。OCR 结果没有可靠 bbox 时只跳页并展示引文。请人工核对 OCR 文本与原始图像，系统无法保证识别文字与扫描图像逐字一致。

## 数据与隐私

- `data/evidenceweave.sqlite3`：案件、文档块、人物、陈述、事实、关系、人工复核。
- `data/documents/<case_id>/<uuid>.pdf`：原始 PDF，保留用户文件名作为元数据；不以用户文件名写路径。
- `data/logs/`：本地服务日志。
- `runtime/models/`：本机交付的 Ollama 模型；源码版可使用既有 Ollama 模型目录。
- `.env`：本地设置。不应提交到公共仓库。

核心分析仅访问本机 Ollama 和 SQLite；浏览器静态资源本地加载。初次安装依赖、下载模型需要网络。数据库和 PDF **没有应用层加密**，应使用设备磁盘加密及操作系统访问控制。备份时停止服务后复制整个 `data/`；不要只复制正在写入的 SQLite 主文件而丢失 WAL。

不提供云同步、云模型、聊天机器人、法律数据库、法律问答或多用户权限系统。上传内容作为待分析材料，不作为模型的系统指令。

## AI 边界与当前限制

模型只提示材料中的证据关系，不判断有罪、可信度、撒谎、法律效力或最终法律意见。置信度是模型输出，不是事实成立概率。

- 别名、模糊事件边界、代词、省略、反讽、嵌套转述仍可能误提取或漏提取，必须人工核验。
- 缺年份、相对日期没有可靠锚点时，不猜具体时间；保留原文并标记低时间精度。地点仅去除空白等轻量规范化，不接地图 API。
- 重点覆盖在场、进入、离开、交付、收款、转账、商议、联系、观察、持有；复杂行为顺序及间接言词证据不保证完整理解。
- 极长原文块按 2400 字分片；句子恰好跨分片边界时可能漏提取。
- 分析在单个本地服务进程中执行，当前不提供任务队列、暂停或跨进程恢复；一次案件分析过程中禁止改材料和人物。
- 新增案件信息后旧结果会标记待更新。初始模型结果与人工复核永不混为一个标签。

## Benchmark 与验证

`benchmark/synthetic_case/` 含 17 份双页 PDF、5 名被告、2 名证人，以及 `gold_labels.json` 中 20 对人工标准关系。另有钱某作为其他相关人物。**全部示例为 synthetic data，不是真实客户材料。**

生成或导入：

```powershell
.venv\Scripts\python scripts\generate_benchmark.py
.venv\Scripts\python scripts\import_demo.py --analyze
```

最小真实链路：

```powershell
.venv\Scripts\python scripts\phase1.py benchmark\synthetic_case\01_张某_第一次讯问.pdf benchmark\synthetic_case\02_张某_第二次讯问.pdf
```

`benchmark/phase1_real_result.json` 是 qwen3:14b 的真实运行记录：4 条事实，1 条 CONTRADICTS、1 条 SUPPORTS，均引用第 2 页。它不是手写的模型返回值。

完整分析完成后运行：

```powershell
.venv\Scripts\python scripts\evaluate_benchmark.py <case_id>
```

输出 `benchmark/last_report.json`，报告固定 20 对关系的矛盾 precision / recall、逐字引文定位准确率、人物 precision / recall 和逐项结果。未抽取到的关键事实计入漏报，不通过删掉失败项提高分数；被候选规则正确排除的无关对作为无关匹配计入。该小型合成集不是实际案件准确率承诺。

当前 qwen3:14b 全集实测：17/17 PDF 导入、34 条事实、94 条关系；矛盾 precision 90.91%、recall 100%，来源定位 100%，人物 precision / recall 100% / 100%，固定 20 对关系准确率 95%。详细环境、修正前基线和未验收边界见 `docs/VALIDATION.md`。

测试：

```powershell
$env:PYTHONPATH = "backend"
.venv\Scripts\python -m pytest backend\tests -q
```

测试隔离在临时 SQLite 中，不改动工作台数据。管线单元测试使用明确标注的测试替身，只验证结构、来源与流程；真实模型质量单独由上述实测报告验证。最终验收记录见 `docs/VALIDATION.md`。

## API 与依赖

任务书约定接口统一位于 `/api` 前缀下，例如 `POST /api/cases`、`POST /api/cases/{id}/documents`、`POST /api/cases/{id}/analyze`、`GET /api/cases/{id}/facts`、`GET /api/cases/{id}/relations`、`POST /api/relations/{id}/review`。人物、目标选择、原始 PDF 和原文块接口一并实现。接口文档在本机 `/docs`。

第三方组件及许可证见 `docs/THIRD_PARTY.md`，其中 PyMuPDF 具有 AGPL / 商业许可条件。使用的开源模型为 Qwen3 14B / 8B。开发过程中使用 OpenAI Codex 辅助代码实现、调试和文档整理；提交的 EvidenceWeave 产品本身完全本地运行，不调用 OpenAI 服务，也不需要 OpenAI 账号或 API Key。
