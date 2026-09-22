# 第三方组件

本项目代码为 MIT。依赖及本地模型各自保留原许可证；本项目的 MIT 不覆盖依赖。

| 组件 | 用途 | 许可证 / 说明 |
|---|---|---|
| React、Vite、Tailwind CSS | 本地前端 | MIT |
| TypeScript | 类型检查 | Apache-2.0 |
| PDF.js | 本地 PDF 显示、页码跳转 | Apache-2.0；静态字体/CMap/wasm 随构建复制 |
| Lucide | 界面图标 | ISC |
| FastAPI、Pydantic、SQLAlchemy | API、结构校验、数据库 | MIT |
| Uvicorn | ASGI 服务 | BSD-3-Clause |
| HTTPX | 本机 Ollama 请求 | BSD-3-Clause |
| PyMuPDF / MuPDF | PDF 解析 | AGPL-3.0 / 商业双许可；闭源分发或商业集成须核对其许可条件 |
| pytest | 自动化测试 | MIT |
| Ollama | 本地模型服务 | MIT；GPU 运行库另有其附带许可 |
| Qwen3 14B / 8B | 本地事实抽取及关系判断 | Apache-2.0；由 Ollama 单独下载，不放进源码压缩包 |
| MinerU | 可选本地 OCR | 未默认安装或捆绑；按实际安装版本及权重许可证使用 |

版本锁：`backend/requirements.txt`、`frontend/package-lock.json`。官方协议参考：
- https://docs.ollama.com/api/chat
- https://docs.ollama.com/capabilities/structured-outputs
- https://pymupdf.readthedocs.io/
- https://mozilla.github.io/pdf.js/

AI 编程工具：OpenAI Codex。运行时没有接入 OpenAI、Claude 或 Gemini API。
