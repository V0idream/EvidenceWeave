import { useEffect, useState, useRef } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  FileText,
  FolderOpen,
  GitCompareArrows,
  Layers3,
  LayoutDashboard,
  Plus,
  Search,
  ShieldCheck,
  Upload,
  Users,
  X,
  Play,
  RefreshCw,
  MessageSquare,
  Clock3,
  AlertTriangle,
  Network,
} from "lucide-react";
import { api, json } from "../api";
import type {
  Case,
  Person,
  Doc,
  Fact,
  Relation,
  Source,
  System,
} from "../types";
import { PdfViewer } from "../components/PdfViewer";

const labels: Record<string, string> = {
  SUPPORTS: "相互印证",
  CONTRADICTS: "潜在矛盾",
  PARTIAL_DIFFERENCE: "有待核实",
  INDEPENDENT: "实际无关",
};
const reviews: Record<string, string> = {
  UNREVIEWED: "待复核",
  CONFIRMED: "已确认",
  DISMISSED: "已否定",
  UNCERTAIN: "不确定",
};
const roles: Record<string, string> = {
  defendant: "被告人",
  witness: "证人",
  victim: "被害人",
  investigator: "调查人员",
  other: "其他 / 待确认",
};
const phases: Record<string, string> = {
  PENDING: "待分析",
  PARSING: "检查材料",
  EXTRACTING: "提取事实",
  NORMALIZING: "标准化",
  MATCHING: "匹配候选",
  VERIFYING: "核验关系",
  COMPLETED: "分析完成",
  FAILED: "分析失败",
};
const types: Record<string, string> = {
  interrogation: "讯问笔录",
  witness_statement: "证人证言",
  victim_statement: "被害人陈述",
  objective_evidence: "客观证据",
  chat_record: "聊天记录",
  bank_record: "银行流水",
  surveillance: "监控摘要",
  other: "其他材料",
};
const sourceTypes: Record<string, string> = {
  self_report: "本人陈述",
  eyewitness: "亲眼所见",
  hearsay: "转述",
  objective: "客观记录",
  unknown: "来源性质待核",
};
const busy = (c: Case | null) =>
  !!c &&
  ["PARSING", "EXTRACTING", "NORMALIZING", "MATCHING", "VERIFYING"].includes(
    c.analysis_status,
  );
const date = (value: string) => new Date(value).toLocaleDateString("zh-CN");
const polarity: Record<string, string> = {
  affirmed: "肯定",
  denied: "否认",
  uncertain: "不确定",
  unknown: "未知",
};
function Badge({
  type,
  children,
}: {
  type: string;
  children?: React.ReactNode;
}) {
  return (
    <span className={"badge " + type}>
      {children || labels[type] || reviews[type] || type}
    </span>
  );
}

export default function App() {
  const [cases, setCases] = useState<Case[]>([]),
    [current, setCurrent] = useState<Case | null>(null),
    [persons, setPersons] = useState<Person[]>([]),
    [docs, setDocs] = useState<Doc[]>([]),
    [facts, setFacts] = useState<Fact[]>([]),
    [relations, setRelations] = useState<Relation[]>([]),
    [system, setSystem] = useState<System | null>(null);
  const [tab, setTab] = useState("overview"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [working, setWorking] = useState(false),
    [create, setCreate] = useState(false),
    [name, setName] = useState(""),
    [description, setDescription] = useState(""),
    [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Relation | null>(null),
    [source, setSource] = useState<Source | null>(null),
    [filter, setFilter] = useState("ALL"),
    [reviewFilter, setReviewFilter] = useState("ALL"),
    [note, setNote] = useState("");
  const [personEdit, setPersonEdit] = useState<Person | null>(null),
    [personName, setPersonName] = useState(""),
    [aliases, setAliases] = useState(""),
    [role, setRole] = useState("other"),
    [personModal, setPersonModal] = useState(false),
    [docEdit, setDocEdit] = useState<Doc | null>(null),
    [mergeTarget, setMergeTarget] = useState("");
  const upload = useRef<HTMLInputElement>(null);
  const currentId = useRef<string | null>(null);
  function person(id: string | null) {
    return persons.find((p) => p.id === id)?.canonical_name || "来源未明确";
  }
  async function loadCases() {
    setCases(await api<Case[]>("/cases"));
  }
  async function refresh(id: string) {
    const [c, p, d, f, r] = await Promise.all([
      api<Case>("/cases/" + id),
      api<Person[]>("/cases/" + id + "/persons"),
      api<Doc[]>("/cases/" + id + "/documents"),
      api<Fact[]>("/cases/" + id + "/facts"),
      api<Relation[]>("/cases/" + id + "/relations"),
    ]);
    if (currentId.current !== id) return;
    setCurrent(c);
    setPersons(p);
    setDocs(d);
    setFacts(f);
    setRelations(r);
  }
  async function run(action: () => Promise<void>) {
    setError("");
    setWorking(true);
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setWorking(false);
    }
  }
  useEffect(() => {
    loadCases().catch((e) => setError(e.message));
    api<System>("/system")
      .then(setSystem)
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (!current) return;
    const id = current.id;
    const timer = setInterval(
      () => {
        refresh(id).catch((e) => setError(e.message));
      },
      busy(current) ? 1800 : 10000,
    );
    return () => clearInterval(timer);
  }, [current?.id, current?.analysis_status]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSource(null);
        setSelected(null);
        setCreate(false);
        setPersonModal(false);
        setDocEdit(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  async function open(c: Case) {
    currentId.current = c.id;
    setCurrent(c);
    setPersons([]);
    setDocs([]);
    setFacts([]);
    setRelations([]);
    setTab("overview");
    setSelected(null);
    setQuery("");
    setError("");
    await run(() => refresh(c.id));
  }
  async function uploadFiles(files: FileList | null) {
    if (!files || !current) return;
    const id = current.id;
    await run(async () => {
      const body = new FormData();
      Array.from(files).forEach((f) => body.append("files", f));
      const result = await api<{
        documents: Doc[];
        errors: { filename: string; error: string }[];
      }>("/cases/" + id + "/documents", { method: "POST", body });
      setNotice(`已导入 ${result.documents.length} 份 PDF`);
      if (result.errors.length)
        setError(
          result.errors.map((e) => e.filename + "：" + e.error).join("\n"),
        );
      await refresh(id);
    });
    if (upload.current) upload.current.value = "";
  }
  function showRelation(r: Relation) {
    setSelected(r);
    setNote(r.review?.note || "");
  }
  function editPerson(p: Person | null) {
    setMergeTarget("");
    setPersonEdit(p);
    setPersonName(p?.canonical_name || "");
    setAliases(p?.aliases.join("，") || "");
    setRole(p?.role || "other");
    setPersonModal(true);
  }
  function documentSource(d: Doc): Source {
    return {
      document_id: d.id,
      filename: d.filename,
      page_number: 1,
      quote: "",
      bbox: null,
      locator_metadata: { width: 0, height: 0 },
      statement_time: d.statement_time,
    };
  }
  const target = persons.find((p) => p.id === current?.target_person_id);
  const counts = {
    conflict: relations.filter((r) => r.relation_type === "CONTRADICTS").length,
    support: relations.filter((r) => r.relation_type === "SUPPORTS").length,
    review: relations.filter(
      (r) => r.review && r.review.review_status !== "UNREVIEWED",
    ).length,
  };
  const filtered = relations.filter(
    (r) =>
      (filter === "ALL" || r.relation_type === filter) &&
      (reviewFilter === "ALL" ||
        (r.review?.review_status || "UNREVIEWED") === reviewFilter) &&
      (!query ||
        [r.fact_a.quote, r.fact_b.quote, r.explanation]
          .join("")
          .includes(query)),
  );
  const groups = Object.entries(Object.groupBy(filtered, (r) => r.issue_key));
  const columns = [
    ...new Set(
      filtered
        .flatMap((r) => [r.fact_a, r.fact_b])
        .map((f) => f.source_person_id || "objective"),
    ),
  ];
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Network size={24} />
          </div>
          <div>
            EvidenceWeave<small>LOCAL EVIDENCE WORKSPACE</small>
          </div>
        </div>
        <button
          className={"nav " + (!current ? "active" : "")}
          onClick={() => {
            currentId.current = null;
            setCurrent(null);
            setQuery("");
            void run(loadCases);
          }}
        >
          <FolderOpen size={18} /> 案件库 <span>{cases.length}</span>
        </button>
        {current && (
          <>
            <div className="section-label">案件工作台</div>
            {[
              ["overview", "概览", LayoutDashboard],
              ["matrix", "一致性矩阵", GitCompareArrows],
              ["evolution", "供述变化", Clock3],
              ["documents", "卷宗材料", FileText],
            ].map(([key, label, Icon]) => (
              <button
                key={key as string}
                className={"nav " + (tab === key ? "active" : "")}
                onClick={() => {
                  setTab(key as string);
                  setQuery("");
                }}
              >
                <Icon size={18} />
                {label as string}
                {key === "documents" && <span>{docs.length}</span>}
              </button>
            ))}
            <div className="side-divider" />
            <div className="section-label">
              案件人物{" "}
              <button
                className="icon"
                onClick={() => editPerson(null)}
                aria-label="添加人物"
              >
                <Plus size={14} />
              </button>
            </div>
            <div className="side-people">
              {persons.map((p) => (
                <button
                  key={p.id}
                  className={
                    "person-nav " + (target?.id === p.id ? "chosen" : "")
                  }
                  onClick={() => editPerson(p)}
                >
                  <span className="avatar">{p.canonical_name.slice(0, 1)}</span>
                  <span>
                    {p.canonical_name}
                    <small>
                      {roles[p.role]}
                      {p.pending_aliases.length ? " · 别名待核验" : ""}
                    </small>
                  </span>
                  {target?.id === p.id && <span className="target-dot" />}
                </button>
              ))}
              {persons.length === 0 && (
                <p className="muted small">
                  导入材料后识别人物，也可手动添加。
                </p>
              )}
            </div>
            <div className="section-label">
              原始卷宗 <span>{docs.length}</span>
            </div>
            <div className="side-documents">
              {docs.map((d) => (
                <button
                  key={d.id}
                  title={d.filename}
                  onClick={() => setSource(documentSource(d))}
                >
                  <FileText size={13} />
                  <span>{d.filename}</span>
                </button>
              ))}
            </div>
          </>
        )}
        <div className="sidebar-bottom">
          <ShieldCheck size={19} />
          <div>
            案件数据留在本机<small>AI flags. Lawyers decide.</small>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div className="breadcrumb">
            工作空间 <ChevronRight size={14} />
            <span>{current?.name || "案件库"}</span>
          </div>
          <button
            className="local-indicator"
            title={
              "Ollama: " +
              (system?.active_model || "未就绪") +
              " · OCR: " +
              (system?.ocr || "检查中")
            }
            onClick={() =>
              void run(async () => {
                setSystem(await api<System>("/system"));
                setNotice("本地状态已刷新");
              })
            }
          >
            <span className={system?.llm_ready ? "dot" : "dot amber"} /> LOCAL
            MODE <ShieldCheck size={14} />
          </button>
        </header>
        <div className="content">
          {error && (
            <div role="alert" className="notice error">
              <AlertTriangle size={18} />
              <span>{error}</span>
              <button
                className="icon"
                onClick={() => setError("")}
                aria-label="关闭错误"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div role="status" className="notice">
              <Check size={16} />
              {notice}
              <button
                className="icon"
                onClick={() => setNotice("")}
                aria-label="关闭提示"
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!current ? (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR LOCAL WORKSPACE</div>
                  <h1>每一条判断，都有据可循。</h1>
                  <p>围绕目标被告，交叉核验人物、陈述与原始卷宗。</p>
                </div>
                <button className="primary" onClick={() => setCreate(true)}>
                  <Plus size={17} /> 新建案件
                </button>
              </div>
              <div className="intro-banner">
                <div className="intro-icon">
                  <Layers3 size={30} />
                </div>
                <div>
                  <h3>从分散材料，到可核验的证据关系</h3>
                  <p>
                    导入 PDF → 选择目标人物 → 本地分析 → 原文定位 → 人工复核
                  </p>
                </div>
                <span className="serif-label">
                  No Citation,
                  <br />
                  No Claim.
                </span>
              </div>
              <div className="section-head">
                <h2>
                  全部案件{" "}
                  <span>{cases.length.toString().padStart(2, "0")}</span>
                </h2>
                <div className="search">
                  <Search size={16} />
                  <input
                    aria-label="搜索案件"
                    placeholder="搜索案件名称"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
              </div>
              <div className="case-grid">
                {cases
                  .filter((c) => c.name.includes(query))
                  .map((c) => (
                    <button
                      key={c.id}
                      className="case-card"
                      onClick={() => void open(c)}
                    >
                      <div className="card-top">
                        <FolderOpen size={25} />
                        <Badge
                          type={
                            c.analysis_status === "COMPLETED"
                              ? "SUPPORTS"
                              : c.analysis_status === "FAILED"
                                ? "CONTRADICTS"
                                : "UNREVIEWED"
                          }
                        >
                          {phases[c.analysis_status]}
                        </Badge>
                      </div>
                      <h3>{c.name}</h3>
                      <p>{c.description || "本地证据交叉核验案件"}</p>
                      <div className="card-footer">
                        <span>
                          <FileText size={14} /> {c.document_count} 份材料
                        </span>
                        <span>{date(c.created_at)}</span>
                        <ArrowUpRight size={18} />
                      </div>
                    </button>
                  ))}
                <button
                  className="case-card create-card"
                  onClick={() => setCreate(true)}
                >
                  <Plus size={28} />
                  <h3>创建新的案件</h3>
                  <p>从第一份卷宗开始</p>
                </button>
              </div>
              <SystemPanel system={system} />
            </>
          ) : (
            <>
              <div className="workspace-heading">
                <div>
                  <div className="eyebrow">
                    CASE WORKSPACE / {current.id.slice(0, 8).toUpperCase()}
                  </div>
                  <h1>{current.name}</h1>
                  <p>
                    {current.description || "所有分析结果均需律师人工核验。"}
                  </p>
                </div>
                <button
                  className="primary"
                  disabled={working || busy(current) || !docs.length}
                  onClick={() =>
                    void run(async () => {
                      await api("/cases/" + current.id + "/analyze", {
                        method: "POST",
                      });
                      await refresh(current.id);
                    })
                  }
                >
                  {busy(current) ? (
                    <RefreshCw size={17} className="spin" />
                  ) : (
                    <Play size={17} />
                  )}{" "}
                  {busy(current)
                    ? "正在本地分析"
                    : current.active_run_id
                      ? "重新分析"
                      : "开始分析"}
                </button>
              </div>
              <div className="focus-bar">
                <div className="focus-label">
                  <Users size={17} />
                  <span>目标被告</span>
                </div>
                <select
                  aria-label="目标被告"
                  value={current.target_person_id || ""}
                  onChange={(e) => {
                    if (e.target.value)
                      void run(async () => {
                        await api(
                          "/cases/" + current.id + "/target-person",
                          json("PATCH", { person_id: e.target.value }),
                        );
                        await refresh(current.id);
                      });
                  }}
                >
                  <option value="" disabled>
                    选择人物以聚焦相关证据
                  </option>
                  {persons.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.canonical_name} · {roles[p.role]}
                    </option>
                  ))}
                </select>
                <span className="focus-hint">
                  {target
                    ? "聚焦本人陈述、他人提及与相关客观证据"
                    : "尚未选择 · 当前显示全案证据"}
                </span>
              </div>
              {current.analysis_status === "PENDING" &&
                current.active_run_id && (
                  <div className="notice">{current.progress}</div>
                )}
              {(busy(current) || current.analysis_status === "FAILED") && (
                <div
                  className={
                    "notice " +
                    (current.analysis_status === "FAILED" ? "error" : "")
                  }
                >
                  <RefreshCw
                    size={17}
                    className={busy(current) ? "spin" : ""}
                  />
                  <div>
                    <strong>
                      {phases[current.analysis_phase]} ·{" "}
                      {phases[current.analysis_status]}
                    </strong>
                    <p>{current.analysis_error || current.progress}</p>
                  </div>
                </div>
              )}
              {tab === "overview" && (
                <>
                  <div className="stats">
                    <Stat
                      title="卷宗材料"
                      value={docs.length}
                      suffix="份"
                      icon={<FileText />}
                    />
                    <Stat
                      title="有来源的原子事实"
                      value={facts.length}
                      suffix="条"
                      icon={<Layers3 />}
                    />
                    <Stat
                      title="潜在矛盾"
                      value={counts.conflict}
                      suffix="处"
                      icon={<GitCompareArrows />}
                      accent
                    />
                    <Stat
                      title="人工复核"
                      value={counts.review}
                      suffix={"/ " + relations.length}
                      icon={<ShieldCheck />}
                    />
                  </div>
                  <div className="overview-grid">
                    <section className="panel">
                      <div className="section-head">
                        <h2>优先核验</h2>
                        <button
                          className="text-btn"
                          onClick={() => setTab("matrix")}
                        >
                          查看一致性矩阵 <ArrowUpRight size={15} />
                        </button>
                      </div>
                      {relations.length ? (
                        <div className="finding-list">
                          {[...relations]
                            .sort(
                              (a, b) =>
                                Number(b.relation_type === "CONTRADICTS") -
                                Number(a.relation_type === "CONTRADICTS"),
                            )
                            .slice(0, 5)
                            .map((r) => (
                              <button
                                className="finding"
                                key={r.id}
                                onClick={() => showRelation(r)}
                              >
                                <div>
                                  <Badge type={r.relation_type} />
                                  <span className="finding-title">
                                    {person(r.fact_a.subject_person_id)} ·{" "}
                                    {r.fact_a.predicate}
                                  </span>
                                </div>
                                <p>{r.explanation}</p>
                                <small>
                                  {person(r.fact_a.source_person_id)} ↔{" "}
                                  {person(r.fact_b.source_person_id)}
                                  <ChevronRight size={15} />
                                </small>
                              </button>
                            ))}
                        </div>
                      ) : (
                        <Empty
                          title="让材料之间的关系浮现"
                          text="导入两份以上 PDF，检查人物与材料日期，然后运行本地分析。"
                          action={
                            <button
                              className="secondary"
                              onClick={() => upload.current?.click()}
                              disabled={working || busy(current)}
                            >
                              <Upload size={16} /> 导入 PDF
                            </button>
                          }
                        />
                      )}
                    </section>
                    <section className="panel workflow">
                      <div className="section-head">
                        <h2>核验流程</h2>
                        <span className="eyebrow">01—04</span>
                      </div>
                      {[
                        [
                          "导入原始卷宗",
                          "文本 PDF 自动解析，扫描页按需 OCR",
                          docs.length > 0,
                        ],
                        [
                          "确认案件人物",
                          "选择目标被告，核对别名与发言者",
                          !!target,
                        ],
                        [
                          "本地交叉分析",
                          "每条原子事实均保留页码与原文",
                          !!current.active_run_id,
                        ],
                        [
                          "律师人工复核",
                          "确认、否定或标记不确定",
                          counts.review > 0,
                        ],
                      ].map(([title, text, done], i) => (
                        <div className="workflow-step" key={String(title)}>
                          <span className={done ? "step done" : "step"}>
                            {done ? <Check size={15} /> : i + 1}
                          </span>
                          <div>
                            <strong>{title}</strong>
                            <p>{text}</p>
                          </div>
                        </div>
                      ))}
                      <div className="workflow-note">
                        AI 发现值得核验的关系。
                        <br />
                        事实与法律判断，始终由律师作出。
                      </div>
                    </section>
                  </div>
                  <SystemPanel system={system} />
                </>
              )}
              {tab === "matrix" && (
                <>
                  <div className="section-head">
                    <div>
                      <h2>
                        一致性矩阵 <span>{relations.length} 条关系</span>
                      </h2>
                      <p className="muted small">
                        按待证问题对照不同来源；点击条目查看双方引文和复核记录。
                      </p>
                    </div>
                    <span className="eyebrow">AI ANALYSIS</span>
                  </div>
                  <div className="filter-row">
                    <div className="filter-tabs">
                      {[
                        ["ALL", "全部"],
                        ["CONTRADICTS", "潜在矛盾"],
                        ["SUPPORTS", "相互印证"],
                        ["PARTIAL_DIFFERENCE", "有待核实"],
                        ["INDEPENDENT", "实际无关"],
                      ].map(([key, label]) => (
                        <button
                          className={filter === key ? "selected" : ""}
                          onClick={() => setFilter(key)}
                          key={key}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                    <select
                      aria-label="复核状态筛选"
                      value={reviewFilter}
                      onChange={(e) => setReviewFilter(e.target.value)}
                    >
                      <option value="ALL">全部复核状态</option>
                      {Object.entries(reviews).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="search matrix-search">
                    <Search size={16} />
                    <input
                      aria-label="搜索引文"
                      placeholder="搜索原文或分析说明"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                    />
                  </div>
                  {groups.length ? (
                    <div className="matrix-wrap">
                      <table className="matrix">
                        <thead>
                          <tr>
                            <th>待证问题 / Issue</th>
                            {columns.map((id) => (
                              <th key={id}>
                                {id === "objective"
                                  ? "客观 / 未指明来源"
                                  : person(id)}
                              </th>
                            ))}
                            <th>关系与人工复核</th>
                          </tr>
                        </thead>
                        <tbody>
                          {groups.map(([key, rs]) => {
                            const rows = rs || [];
                            const fs = [
                              ...new Map(
                                rows
                                  .flatMap((r) => [r.fact_a, r.fact_b])
                                  .map((f) => [f.id, f]),
                              ).values(),
                            ];
                            return (
                              <tr key={key}>
                                <th>
                                  <div>
                                    {person(rows[0].fact_a.subject_person_id)} ·{" "}
                                    {rows[0].fact_a.predicate}
                                  </div>
                                  <small>
                                    {rows[0].fact_a.time_text || "时间待核验"}
                                  </small>
                                  <span>{rows.length} 条关系</span>
                                </th>
                                {columns.map((id) => (
                                  <td key={id}>
                                    {fs
                                      .filter(
                                        (f) =>
                                          (f.source_person_id ||
                                            "objective") === id,
                                      )
                                      .map((f) => (
                                        <button
                                          className="matrix-fact"
                                          key={f.id}
                                          onClick={() => setSource(f.source)}
                                        >
                                          <small>
                                            {polarity[f.polarity]} · P.
                                            {f.page_number}
                                          </small>
                                          <span>{f.quote}</span>
                                          <span className="citation-link">
                                            <FileText size={12} /> 原文
                                          </span>
                                        </button>
                                      ))}
                                  </td>
                                ))}
                                <td>
                                  {rows.map((r) => (
                                    <button
                                      className="relation-cell"
                                      key={r.id}
                                      onClick={() => showRelation(r)}
                                    >
                                      <Badge type={r.relation_type} />
                                      <small>
                                        {
                                          reviews[
                                            r.review?.review_status ||
                                              "UNREVIEWED"
                                          ]
                                        }{" "}
                                        <ChevronRight size={12} />
                                      </small>
                                    </button>
                                  ))}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <Empty
                      title="暂无符合筛选的关系"
                      text={
                        relations.length
                          ? "请调整关系或复核状态筛选。"
                          : "完成本地分析后，候选事实关系将在这里显示。"
                      }
                    />
                  )}
                </>
              )}
              {tab === "evolution" && (
                <>
                  <div className="section-head">
                    <div>
                      <h2>供述变化</h2>
                      <p className="muted small">
                        按陈述日期排列同一人的材料；日期缺失时明确标记，不推断先后。
                      </p>
                    </div>
                    <Clock3 size={22} />
                  </div>
                  {persons
                    .filter((p) =>
                      facts.some((f) => f.source_person_id === p.id),
                    )
                    .map((p) => {
                      const pf = facts.filter(
                        (f) => f.source_person_id === p.id,
                      );
                      const byDoc = Object.values(
                        Object.groupBy(pf, (f) => f.document_id),
                      )
                        .filter((x): x is Fact[] => !!x)
                        .sort((a, b) =>
                          (a[0].source.statement_time || "9999").localeCompare(
                            b[0].source.statement_time || "9999",
                          ),
                        );
                      const changes = relations.filter(
                        (r) =>
                          r.fact_a.source_person_id === p.id &&
                          r.fact_b.source_person_id === p.id &&
                          r.fact_a.document_id !== r.fact_b.document_id &&
                          ["CONTRADICTS", "PARTIAL_DIFFERENCE"].includes(
                            r.relation_type,
                          ),
                      );
                      return (
                        <section className="panel evolution" key={p.id}>
                          <h3>
                            <span className="avatar">
                              {p.canonical_name[0]}
                            </span>
                            {p.canonical_name}
                            <span className="muted small">
                              {byDoc.length} 份材料
                            </span>
                          </h3>
                          {changes.length > 0 && (
                            <div className="change-flags">
                              {changes.map((r) => (
                                <button
                                  className="text-btn"
                                  key={r.id}
                                  onClick={() => showRelation(r)}
                                >
                                  <GitCompareArrows size={14} /> 关于“
                                  {r.fact_a.predicate}”的陈述存在
                                  {labels[r.relation_type]}
                                </button>
                              ))}
                            </div>
                          )}
                          <div className="timeline">
                            {byDoc.map((fs) => (
                              <div
                                className="timeline-entry"
                                key={fs[0].document_id}
                              >
                                <span className="timeline-dot" />
                                <small>
                                  {fs[0].source.statement_time ||
                                    "陈述日期未确认"}
                                </small>
                                <h4>{fs[0].source.filename}</h4>
                                {fs.map((f) => (
                                  <button
                                    className="quote-line"
                                    key={f.id}
                                    onClick={() => setSource(f.source)}
                                  >
                                    <span>{f.quote}</span>
                                    <span className="citation-link">
                                      P.{f.page_number}{" "}
                                      <ArrowUpRight size={12} />
                                    </span>
                                  </button>
                                ))}
                              </div>
                            ))}
                          </div>
                        </section>
                      );
                    })}
                  {!facts.length && (
                    <Empty
                      title="尚无供述记录"
                      text="分析材料后，这里会显示有来源的陈述时间线。"
                    />
                  )}
                </>
              )}
              {tab === "documents" && (
                <>
                  <div className="section-head">
                    <div>
                      <h2>
                        卷宗材料 <span>{docs.length} 份</span>
                      </h2>
                      <p className="muted small">
                        原始 PDF
                        保留于本机；补充发言者和陈述日期后，请重新分析以更新事实。
                      </p>
                    </div>
                    <button
                      className="primary"
                      disabled={working || busy(current)}
                      onClick={() => upload.current?.click()}
                    >
                      <Upload size={17} /> 批量导入 PDF
                    </button>
                  </div>
                  <div
                    className="upload-zone"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      if (!working && !busy(current))
                        void uploadFiles(e.dataTransfer.files);
                    }}
                  >
                    <Upload size={25} />
                    <strong>
                      {working
                        ? "正在导入并逐页解析…"
                        : "拖入 PDF 文件，保留每一页的出处"}
                    </strong>
                    <span>
                      支持多文件 · 单份最大 100 MB · 扫描件需本地 MinerU
                    </span>
                  </div>
                  <div className="document-list">
                    {docs.map((d) => (
                      <div className="document-row" key={d.id}>
                        <div className="doc-icon">
                          <FileText size={22} />
                        </div>
                        <div className="doc-info">
                          <button
                            className="document-name"
                            onClick={() => setSource(documentSource(d))}
                          >
                            {d.filename}
                          </button>
                          <small>
                            {types[d.document_type]} · {d.total_pages} 页 ·{" "}
                            {person(d.source_person_id)} ·{" "}
                            {d.statement_time || "日期未确认"}
                          </small>
                          {d.warnings.map((w, i) => (
                            <p className="warning-text" key={i}>
                              <AlertTriangle size={13} />
                              {w}
                            </p>
                          ))}
                        </div>
                        <Badge
                          type={
                            d.processing_status === "READY"
                              ? "SUPPORTS"
                              : "PARTIAL_DIFFERENCE"
                          }
                        >
                          {d.processing_status === "READY"
                            ? "已解析"
                            : "需检查"}
                        </Badge>
                        <button
                          className="secondary small"
                          disabled={busy(current)}
                          onClick={() => setDocEdit({ ...d })}
                        >
                          材料信息
                        </button>
                        <button
                          className="icon"
                          onClick={() => setSource(documentSource(d))}
                          aria-label={"打开 " + d.filename}
                        >
                          <ArrowUpRight size={18} />
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}
              <input
                ref={upload}
                type="file"
                multiple
                accept="application/pdf,.pdf"
                hidden
                onChange={(e) => void uploadFiles(e.target.files)}
              />
            </>
          )}
          <footer>
            <span>EvidenceWeave V1</span>
            <span>
              No Citation, No Claim. <span className="footer-dot">·</span> AI
              flags. Lawyers decide.
            </span>
          </footer>
        </div>
      </main>
      {create && (
        <div
          className="modal-shade"
          role="dialog"
          aria-modal="true"
          aria-label="新建案件"
        >
          <form
            className="form-modal"
            onSubmit={(e) => {
              e.preventDefault();
              void run(async () => {
                const c = await api<Case>(
                  "/cases",
                  json("POST", { name, description }),
                );
                setCreate(false);
                setName("");
                setDescription("");
                await loadCases();
                await open(c);
              });
            }}
          >
            <header>
              <h2>新建案件</h2>
              <button
                type="button"
                className="icon"
                onClick={() => setCreate(false)}
                aria-label="关闭"
              >
                <X />
              </button>
            </header>
            <p className="muted">案件及材料仅保存在当前设备。</p>
            <label>
              案件名称
              <input
                autoFocus
                required
                maxLength={120}
                placeholder="例如：鑫源宾馆案（虚构示例）"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label>
              案件说明
              <textarea
                placeholder="用于区分案件的简短说明"
                maxLength={4000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
            <button className="primary" disabled={working || !name.trim()}>
              创建并打开案件 <ArrowUpRight size={16} />
            </button>
          </form>
        </div>
      )}
      {personModal && (
        <div
          className="modal-shade"
          role="dialog"
          aria-modal="true"
          aria-label="人物信息"
        >
          <form
            className="form-modal"
            onSubmit={(e) => {
              e.preventDefault();
              if (!current) return;
              void run(async () => {
                await api(
                  personEdit
                    ? "/persons/" + personEdit.id
                    : "/cases/" + current.id + "/persons",
                  json(personEdit ? "PATCH" : "POST", {
                    canonical_name: personName,
                    role,
                    aliases: aliases
                      .split(/[,，\n]/)
                      .map((x) => x.trim())
                      .filter(Boolean),
                  }),
                );
                setPersonModal(false);
                await refresh(current.id);
              });
            }}
          >
            <header>
              <h2>{personEdit ? "核验人物信息" : "添加案件人物"}</h2>
              <button
                type="button"
                className="icon"
                onClick={() => setPersonModal(false)}
                aria-label="关闭人物信息"
              >
                <X />
              </button>
            </header>
            <label>
              规范姓名
              <input
                required
                value={personName}
                onChange={(e) => setPersonName(e.target.value)}
              />
            </label>
            <label>
              人物角色
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                {Object.entries(roles).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label>
              已人工确认的别名
              <textarea
                value={aliases}
                onChange={(e) => setAliases(e.target.value)}
                placeholder="用逗号分隔，例如：小张，张总"
              />
            </label>
            {!!personEdit?.pending_aliases.length && (
              <p className="warning-text">
                可能相关人物：{personEdit.pending_aliases.join("、")}
                。系统未自动合并。
              </p>
            )}
            <p className="muted small">
              别名将用于后续分析。请仅填写已经核实属于此人的称呼；已有其他人物姓名不能直接占用。
            </p>
            <button className="primary" disabled={working || busy(current)}>
              保存人物信息
            </button>
            {personEdit && (
              <div className="merge-section">
                <label>
                  核实为同一人后，合并到
                  <select
                    aria-label="合并目标人物"
                    value={mergeTarget}
                    onChange={(e) => setMergeTarget(e.target.value)}
                  >
                    <option value="">选择已确认的规范人物</option>
                    {persons
                      .filter((p) => p.id !== personEdit.id)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.canonical_name}
                        </option>
                      ))}
                  </select>
                </label>
                <p className="muted small">
                  原姓名将成为别名，引用和复核保留。仅在已确认两者为同一人时操作。
                </p>
                <button
                  type="button"
                  className="secondary"
                  disabled={!mergeTarget || working || busy(current)}
                  onClick={() => {
                    if (!current) return;
                    void run(async () => {
                      await api(
                        "/persons/" + personEdit.id + "/merge",
                        json("POST", {
                          target_person_id: mergeTarget,
                          confirmed_same_person: true,
                        }),
                      );
                      setPersonModal(false);
                      setNotice("已合并人物；请重新分析更新候选关系");
                      await refresh(current.id);
                    });
                  }}
                >
                  我已核实，合并人物
                </button>
              </div>
            )}
          </form>
        </div>
      )}
      {docEdit && (
        <div
          className="modal-shade"
          role="dialog"
          aria-modal="true"
          aria-label="材料信息"
        >
          <form
            className="form-modal"
            onSubmit={(e) => {
              e.preventDefault();
              if (!current) return;
              void run(async () => {
                await api(
                  "/documents/" + docEdit.id,
                  json("PATCH", {
                    document_type: docEdit.document_type,
                    source_person_id: docEdit.source_person_id,
                    statement_time: docEdit.statement_time || null,
                  }),
                );
                setDocEdit(null);
                await refresh(current.id);
              });
            }}
          >
            <header>
              <h2>材料信息</h2>
              <button
                type="button"
                className="icon"
                onClick={() => setDocEdit(null)}
                aria-label="关闭材料信息"
              >
                <X />
              </button>
            </header>
            <p>{docEdit.filename}</p>
            <label>
              材料类型
              <select
                value={docEdit.document_type}
                onChange={(e) =>
                  setDocEdit({ ...docEdit, document_type: e.target.value })
                }
              >
                {Object.entries(types).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label>
              陈述人
              <select
                value={docEdit.source_person_id || ""}
                onChange={(e) =>
                  setDocEdit({
                    ...docEdit,
                    source_person_id: e.target.value || null,
                  })
                }
              >
                <option value="">未明确 / 客观记录</option>
                {persons.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.canonical_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              讯问 / 陈述日期
              <input
                type="date"
                value={docEdit.statement_time || ""}
                onChange={(e) =>
                  setDocEdit({ ...docEdit, statement_time: e.target.value })
                }
              />
            </label>
            <button className="primary" disabled={working}>
              保存
            </button>
          </form>
        </div>
      )}
      {selected && (
        <div className="drawer-shade" onClick={() => setSelected(null)}>
          <section
            className="detail-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="证据关系详情"
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <div>
                <small>EVIDENCE DETAIL</small>
                <h2>证据关系核验</h2>
              </div>
              <button
                className="icon"
                onClick={() => setSelected(null)}
                aria-label="关闭关系详情"
              >
                <X />
              </button>
            </header>
            <div className="drawer-body">
              <div className="ai-result">
                <div>
                  <span className="eyebrow">AI ANALYSIS</span>
                  <Badge type={selected.relation_type} />
                </div>
                <p>{selected.explanation}</p>
                <small>
                  模型置信度 {Math.round(selected.confidence * 100)}% ·
                  不是事实成立的概率
                </small>
              </div>
              {[selected.fact_a, selected.fact_b].map((f, i) => (
                <section className="fact-card" key={f.id}>
                  <div className="fact-heading">
                    <span>FACT {i ? "B" : "A"}</span>
                    <strong>{person(f.source_person_id)}</strong>
                    <Badge type="INDEPENDENT">
                      {sourceTypes[f.source_type]}
                    </Badge>
                  </div>
                  <blockquote>{f.quote}</blockquote>
                  <div className="fact-meta">
                    <span>
                      {f.predicate} · {polarity[f.polarity]}
                    </span>
                    <span>{f.time_text || "时间未明确"}</span>
                    {f.amount !== null && (
                      <span>金额 ¥{f.amount.toLocaleString()}</span>
                    )}
                  </div>
                  <button
                    className="source-button"
                    onClick={() => setSource(f.source)}
                  >
                    <FileText size={16} />
                    <span>
                      {f.source.filename}
                      <small>第 {f.page_number} 页 · 查看原文定位</small>
                    </span>
                    <ArrowUpRight size={17} />
                  </button>
                </section>
              ))}
              <section className="review-box">
                <div className="section-head">
                  <h3>
                    <ShieldCheck size={18} /> 律师人工复核
                  </h3>
                  <Badge
                    type={selected.review?.review_status || "UNREVIEWED"}
                  />
                </div>
                <p>复核状态独立保存，不改变上方 AI 初始判断。</p>
                <textarea
                  aria-label="复核备注"
                  placeholder="记录核验依据、疑问或后续调查方向…"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
                <div className="review-actions">
                  {[
                    ["CONFIRMED", "确认"],
                    ["DISMISSED", "否定"],
                    ["UNCERTAIN", "不确定"],
                  ].map(([status, label]) => (
                    <button
                      className={
                        status === "CONFIRMED" ? "primary" : "secondary"
                      }
                      key={status}
                      disabled={working}
                      onClick={() =>
                        void run(async () => {
                          await api<
                            NonNullable<Relation["review"]>
                          >(
                            "/relations/" + selected.id + "/review",
                            json("POST", { review_status: status, note }),
                          );
                          const next = relations.find(
                            (relation) =>
                              relation.issue_key === selected.issue_key &&
                              relation.relation_type ===
                                selected.relation_type &&
                              relation.id !== selected.id &&
                              (!relation.review ||
                                relation.review.review_status === "UNREVIEWED"),
                          );
                          if (current) await refresh(current.id);
                          if (next) {
                            showRelation(next);
                            setNotice(
                              "人工复核已保存，已跳转到同项同板块下一条",
                            );
                          } else {
                            setSelected(null);
                            setNote("");
                            setNotice(
                              "人工复核已保存，该项当前板块已全部复核",
                            );
                          }
                        })
                      }
                    >
                      {status === "CONFIRMED" ? (
                        <Check size={15} />
                      ) : status === "DISMISSED" ? (
                        <X size={15} />
                      ) : (
                        <MessageSquare size={15} />
                      )}{" "}
                      {label}
                    </button>
                  ))}
                </div>
              </section>
            </div>
          </section>
        </div>
      )}
      {source && <PdfViewer source={source} onClose={() => setSource(null)} />}
    </div>
  );
}
function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <GitCompareArrows size={34} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}
function Stat({
  title,
  value,
  suffix,
  icon,
  accent = false,
}: {
  title: string;
  value: number;
  suffix: string;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div className={"stat " + (accent ? "accent" : "")}>
      <div>
        {title}
        {icon}
      </div>
      <strong>
        {value}
        <small>{suffix}</small>
      </strong>
    </div>
  );
}
function SystemPanel({ system }: { system: System | null }) {
  return (
    <div className="system-panel">
      <span>
        <ShieldCheck size={17} /> 本地运行状态
      </span>
      <span>
        LLM <b>{system?.active_model || "Ollama 未就绪"}</b>
      </span>
      <span>
        Parser <b>PyMuPDF</b>
      </span>
      <span>
        OCR{" "}
        <b>
          {system?.ocr === "unavailable" ? "未安装" : system?.ocr || "检查中"}
        </b>
      </span>
      <span>
        Database <b>SQLite</b>
      </span>
      <span>
        External AI <b>Disabled</b>
      </span>
    </div>
  );
}
