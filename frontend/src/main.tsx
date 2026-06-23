import React from "react";
import ReactDOM from "react-dom/client";
import {
  BriefcaseBusiness,
  ClipboardCheck,
  ExternalLink,
  FileSearch,
  FileUp,
  History,
  Loader2,
  RotateCcw,
  Search,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const HISTORY_STORAGE_KEY = "job-search-copilot-history";
const MAX_HISTORY_RECORDS = 12;

type SkillGap = {
  skill: string;
  evidence: string;
  recommendation: string;
};

type ResumeBullet = {
  original_focus: string;
  rewritten_bullet: string;
  evidence_keyword: string | null;
  evidence_source: string | null;
  evidence_snippet: string | null;
  grounded: boolean;
};

type EvidenceSnippet = {
  keyword: string;
  source: string;
  snippet: string;
  relevance_score: number;
};

type AnalyzeResponse = {
  match_score: number;
  summary: string;
  matched_keywords: string[];
  missing_keywords: string[];
  evidence_snippets: EvidenceSnippet[];
  skill_gaps: SkillGap[];
  tailored_bullets: ResumeBullet[];
  interview_questions: string[];
  next_actions: string[];
};

type AppConfig = {
  llm_enabled: boolean;
  llm_provider: string;
  active_model: string;
  bullet_generation: string;
};

type ParseResumeResponse = {
  text: string;
  method: string;
  needs_review: boolean;
  warnings: string[];
  raw_text_length: number;
};

type ParsePreview = ParseResumeResponse & {
  fileName: string;
};

type ResearchSource = {
  title: string;
  url: string;
  content: string;
  score: number;
};

type JobResearchResponse = {
  research_summary: string;
  company_signals: string[];
  role_signals: string[];
  resume_positioning_advice: string[];
  interview_strategy: string[];
  resume_rewrite_suggestions: string[];
  cover_letter_draft: string;
  sources: ResearchSource[];
  used_search: boolean;
  llm_validation_status: string;
  llm_json_repaired: boolean;
  warnings: string[];
};

type HistoryRecord = {
  id: string;
  created_at: string;
  company: string;
  role_title: string;
  resume_text: string;
  job_description: string;
  supplemental_materials: string;
  result: AnalyzeResponse;
  research: JobResearchResponse | null;
};

const sampleResume = `Python 后端工程师，熟悉 FastAPI、React、Docker、Postgres 和 AI Agent 项目开发。
曾为内部知识库构建 RAG 原型，并将 API 延迟降低 35%。
参与简历解析、OCR、LLM 字段清洗和评估指标建设。`;

const sampleJob = `我们正在招聘 AI 工程师，负责构建用于职位匹配和业务自动化的 Agent 工作流。
岗位需要 Python、FastAPI、LangGraph、RAG、Postgres、Docker、评估体系和生产级 API 经验。
工程师将与产品和设计团队协作，交付可靠的 human-in-the-loop AI 工具。`;

const sampleSupplementalMaterials = `项目经历：使用 LangGraph 设计多节点 Agent 工作流，包含需求提取、证据检索、评分、简历 bullet 生成和人工审核节点。
项目经历：使用 LlamaIndex 思路整理简历、项目说明和岗位描述，为后续 RAG 检索预留资料库接口。
GitHub 项目：构建求职 Copilot，使用 FastAPI 提供分析接口，并用 React 实现中文求职工作台。`;

function App() {
  const [resumeText, setResumeText] = React.useState(sampleResume);
  const [jobDescription, setJobDescription] = React.useState(sampleJob);
  const [supplementalMaterials, setSupplementalMaterials] = React.useState(
    sampleSupplementalMaterials,
  );
  const [company, setCompany] = React.useState("ExampleCo");
  const [roleTitle, setRoleTitle] = React.useState("AI 工程师");
  const [result, setResult] = React.useState<AnalyzeResponse | null>(null);
  const [research, setResearch] = React.useState<JobResearchResponse | null>(null);
  const [historyRecords, setHistoryRecords] = React.useState<HistoryRecord[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = React.useState("");
  const [config, setConfig] = React.useState<AppConfig | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [researchLoading, setResearchLoading] = React.useState(false);
  const [parsingResume, setParsingResume] = React.useState(false);
  const [parsePreview, setParsePreview] = React.useState<ParsePreview | null>(null);
  const [parseStatus, setParseStatus] = React.useState("");
  const [error, setError] = React.useState("");
  const [researchError, setResearchError] = React.useState("");

  React.useEffect(() => {
    fetch(`${API_BASE_URL}/config`)
      .then((response) => response.json())
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  React.useEffect(() => {
    const stored = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!stored) {
      return;
    }
    try {
      setHistoryRecords(JSON.parse(stored) as HistoryRecord[]);
    } catch {
      window.localStorage.removeItem(HISTORY_STORAGE_KEY);
    }
  }, []);

  function persistHistory(nextRecords: HistoryRecord[]) {
    setHistoryRecords(nextRecords);
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(nextRecords));
  }

  function saveHistoryRecord(nextResult: AnalyzeResponse, nextResearch: JobResearchResponse | null) {
    const record: HistoryRecord = {
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
      company,
      role_title: roleTitle,
      resume_text: resumeText,
      job_description: jobDescription,
      supplemental_materials: supplementalMaterials,
      result: nextResult,
      research: nextResearch,
    };
    const nextRecords = [record, ...historyRecords].slice(0, MAX_HISTORY_RECORDS);
    persistHistory(nextRecords);
    setSelectedHistoryId(record.id);
    return record.id;
  }

  function updateHistoryResearch(recordId: string, nextResearch: JobResearchResponse) {
    const nextRecords = historyRecords.map((record) =>
      record.id === recordId ? { ...record, research: nextResearch } : record,
    );
    persistHistory(nextRecords);
  }

  function restoreHistory(record: HistoryRecord) {
    setCompany(record.company);
    setRoleTitle(record.role_title);
    setResumeText(record.resume_text);
    setJobDescription(record.job_description);
    setSupplementalMaterials(record.supplemental_materials);
    setResult(record.result);
    setResearch(record.research);
    setSelectedHistoryId(record.id);
    setError("");
    setResearchError("");
  }

  function deleteHistory(recordId: string) {
    const nextRecords = historyRecords.filter((record) => record.id !== recordId);
    persistHistory(nextRecords);
    if (selectedHistoryId === recordId) {
      setSelectedHistoryId("");
    }
  }

  function clearHistory() {
    persistHistory([]);
    setSelectedHistoryId("");
  }

  async function analyze() {
    setLoading(true);
    setError("");
    setResearchError("");
    setResearch(null);
    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription,
          supplemental_materials: supplementalMaterials,
          company,
          role_title: roleTitle,
        }),
      });
      if (!response.ok) {
        throw new Error(`接口返回异常：${response.status}`);
      }
      const data = (await response.json()) as AnalyzeResponse;
      setResult(data);
      saveHistoryRecord(data, null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "暂时无法分析这个岗位匹配度。");
    } finally {
      setLoading(false);
    }
  }

  async function researchTargetJob() {
    setResearchLoading(true);
    setResearchError("");
    try {
      const response = await fetch(`${API_BASE_URL}/research-job`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company,
          role_title: roleTitle,
          job_description: jobDescription,
          resume_text: resumeText,
          supplemental_materials: supplementalMaterials,
        }),
      });
      if (!response.ok) {
        throw new Error(`岗位研究接口返回异常：${response.status}`);
      }
      const data = (await response.json()) as JobResearchResponse;
      setResearch(data);
      if (selectedHistoryId) {
        updateHistoryResearch(selectedHistoryId, data);
      } else if (result) {
        saveHistoryRecord(result, data);
      }
    } catch (err) {
      setResearchError(err instanceof Error ? err.message : "暂时无法完成联网岗位研究。");
    } finally {
      setResearchLoading(false);
    }
  }

  async function uploadResume(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) {
      return;
    }

    setParsingResume(true);
    setParseStatus("");
    setParsePreview(null);
    setError("");
    try {
      const lowerName = file.name.toLowerCase();
      if (lowerName.endsWith(".txt") || lowerName.endsWith(".md")) {
        const text = await file.text();
        setParsePreview({
          fileName: file.name,
          text,
          method: "text_file",
          needs_review: false,
          warnings: ["请确认解析结果无误后再用于分析。"],
          raw_text_length: text.length,
        });
        setParseStatus(`已读取 ${file.name}，等待确认。`);
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/parse-resume`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`简历解析接口返回异常：${response.status}`);
      }
      const parsed = (await response.json()) as ParseResumeResponse;
      setParsePreview({ ...parsed, fileName: file.name });
      setParseStatus(`解析完成：${parseMethodLabel(parsed.method)}，等待确认。`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "简历解析失败，请手动复制粘贴。");
    } finally {
      setParsingResume(false);
    }
  }

  function acceptParsedResume() {
    if (!parsePreview) {
      return;
    }
    setResumeText(parsePreview.text);
    setParseStatus(`已使用 ${parsePreview.fileName} 的解析结果。`);
    setParsePreview(null);
  }

  return (
    <main className="shell">
      <section className="topbar">
        <div>
          <div className="brand">
            <BriefcaseBusiness size={24} />
            <span>求职 Copilot</span>
          </div>
          <p>用 Agent 工作流完成简历定制、岗位匹配分析和面试准备。</p>
        </div>
        {config && (
          <div className="mode-pill">
            {modeLabel(config)}
            <span>{config.active_model}</span>
          </div>
        )}
        <button className="primary" onClick={analyze} disabled={loading}>
          {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          开始分析
        </button>
      </section>

      <section className="workspace">
        <section className="panel inputs">
          <div className="field-row">
            <label>
              公司
              <input value={company} onChange={(event) => setCompany(event.target.value)} />
            </label>
            <label>
              岗位
              <input value={roleTitle} onChange={(event) => setRoleTitle(event.target.value)} />
            </label>
          </div>

          <HistoryPanel
            records={historyRecords}
            selectedId={selectedHistoryId}
            onRestore={restoreHistory}
            onDelete={deleteHistory}
            onClear={clearHistory}
          />

          <label>
            简历内容
            <div className="upload-row">
              <input
                id="resume-upload"
                type="file"
                accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
                onChange={uploadResume}
              />
              <label className="upload-button" htmlFor="resume-upload">
                {parsingResume ? <Loader2 className="spin" size={16} /> : <FileUp size={16} />}
                上传简历
              </label>
              {parseStatus && <span>{parseStatus}</span>}
            </div>
            {parsePreview && (
              <section className="parse-preview">
                <header>
                  <div>
                    <strong>{parsePreview.fileName}</strong>
                    <span>
                      {parseMethodLabel(parsePreview.method)} / {parsePreview.raw_text_length} 字符
                    </span>
                  </div>
                  <button type="button" onClick={() => setParsePreview(null)} aria-label="关闭预览">
                    <X size={16} />
                  </button>
                </header>
                {parsePreview.warnings.length > 0 && (
                  <div className="preview-warnings">
                    {parsePreview.warnings.map((warning) => (
                      <p key={warning}>{warning}</p>
                    ))}
                  </div>
                )}
                <textarea
                  className="preview-textarea"
                  value={parsePreview.text}
                  onChange={(event) =>
                    setParsePreview({ ...parsePreview, text: event.target.value })
                  }
                />
                <footer>
                  <button type="button" className="secondary" onClick={() => setParsePreview(null)}>
                    取消
                  </button>
                  <button type="button" className="primary small" onClick={acceptParsedResume}>
                    使用解析结果
                  </button>
                </footer>
              </section>
            )}
            <textarea value={resumeText} onChange={(event) => setResumeText(event.target.value)} />
          </label>
          <label>
            岗位描述
            <textarea
              value={jobDescription}
              onChange={(event) => setJobDescription(event.target.value)}
            />
          </label>
          <label>
            补充材料 / 项目经历
            <textarea
              className="compact-textarea"
              value={supplementalMaterials}
              onChange={(event) => setSupplementalMaterials(event.target.value)}
            />
          </label>
        </section>

        <section className="panel results">
          {error && <div className="error">{error}</div>}
          {!result && !error && (
            <div className="empty">
              <Sparkles size={28} />
              <p>点击开始分析，生成一份针对该岗位的求职策略简报。</p>
            </div>
          )}
          {result && (
            <>
              <header className="score-row">
                <div className="score">{result.match_score}</div>
                <div>
                  <h1>初始匹配分</h1>
                  <p>{result.summary}</p>
                </div>
              </header>

              <ResearchPanel
                research={research}
                loading={researchLoading}
                error={researchError}
                onResearch={researchTargetJob}
              />

              <ResultBlock title="已匹配关键词" items={result.matched_keywords} tone="good" />
              <ResultBlock title="待补强关键词" items={result.missing_keywords} tone="warn" />

              <section>
                <h2>简历证据</h2>
                <div className="list">
                  {result.evidence_snippets.length === 0 && (
                    <span className="muted">暂未找到可支撑关键词的简历证据</span>
                  )}
                  {result.evidence_snippets.map((evidence) => (
                    <article key={`${evidence.keyword}-${evidence.snippet}`} className="item">
                      <div className="item-title">
                        <FileSearch size={16} />
                        <strong>{evidence.keyword}</strong>
                        <em>{sourceLabel(evidence.source)}</em>
                        <span>{Math.round(evidence.relevance_score * 100)}%</span>
                      </div>
                      <p>{evidence.snippet}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section>
                <h2>能力缺口</h2>
                <div className="list">
                  {result.skill_gaps.map((gap) => (
                    <article key={gap.skill} className="item">
                      <strong>{gap.skill}</strong>
                      <p>{gap.recommendation}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section>
                <h2>定制简历 Bullet</h2>
                <div className="list">
                  {result.tailored_bullets.map((bullet) => (
                    <article key={bullet.original_focus} className="item">
                      <div className="item-title">
                        <strong>{bullet.evidence_keyword ?? "建议"}</strong>
                        <em>
                          {bullet.grounded
                            ? `有证据支撑 / ${sourceLabel(bullet.evidence_source ?? "")}`
                            : "需补充证据"}
                        </em>
                        <span className={bullet.grounded ? "status-good" : "status-warn"}>
                          {bullet.grounded ? "可改写" : "待补充"}
                        </span>
                      </div>
                      <small>{bullet.original_focus}</small>
                      <p>{bullet.rewritten_bullet}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section>
                <h2>面试准备</h2>
                <div className="checklist">
                  {result.interview_questions.map((question) => (
                    <div key={question}>
                      <ClipboardCheck size={16} />
                      <span>{question}</span>
                    </div>
                  ))}
                </div>
              </section>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

function HistoryPanel({
  records,
  selectedId,
  onRestore,
  onDelete,
  onClear,
}: {
  records: HistoryRecord[];
  selectedId: string;
  onRestore: (record: HistoryRecord) => void;
  onDelete: (recordId: string) => void;
  onClear: () => void;
}) {
  return (
    <section className="history-panel">
      <header>
        <div>
          <History size={16} />
          <strong>历史记录</strong>
        </div>
        {records.length > 0 && (
          <button type="button" className="icon-button" onClick={onClear} aria-label="清空历史记录">
            <Trash2 size={15} />
          </button>
        )}
      </header>
      {records.length === 0 && <p className="muted">完成一次分析后会自动保存到本机浏览器。</p>}
      {records.length > 0 && (
        <div className="history-list">
          {records.map((record) => (
            <article
              key={record.id}
              className={record.id === selectedId ? "history-item active" : "history-item"}
            >
              <button type="button" onClick={() => onRestore(record)}>
                <strong>{record.role_title || "未命名岗位"}</strong>
                <span>{record.company || "未命名公司"}</span>
                <small>
                  {formatDateTime(record.created_at)} / {record.result.match_score} 分
                  {record.research ? " / 已研究" : ""}
                </small>
              </button>
              <div className="history-actions">
                <button type="button" onClick={() => onRestore(record)} aria-label="恢复记录">
                  <RotateCcw size={15} />
                </button>
                <button type="button" onClick={() => onDelete(record.id)} aria-label="删除记录">
                  <Trash2 size={15} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ResearchPanel({
  research,
  loading,
  error,
  onResearch,
}: {
  research: JobResearchResponse | null;
  loading: boolean;
  error: string;
  onResearch: () => void;
}) {
  return (
    <section className="research-panel">
      <header>
        <div>
          <h2>岗位研究 RAG</h2>
          <p>检索公司和岗位近期资料，再让 LLM 基于来源输出定位建议。</p>
        </div>
        <button type="button" className="secondary" onClick={onResearch} disabled={loading}>
          {loading ? <Loader2 className="spin" size={16} /> : <Search size={16} />}
          联网研究岗位
        </button>
      </header>

      {error && <div className="error">{error}</div>}
      {research?.warnings.map((warning) => (
        <div className="notice" key={warning}>
          {warning}
        </div>
      ))}
      {research && (
        <div className="research-content">
          <p>{research.research_summary}</p>
          <div className="research-grid">
            <ResearchList title="公司信号" items={research.company_signals} />
            <ResearchList title="岗位信号" items={research.role_signals} />
            <ResearchList title="简历定位建议" items={research.resume_positioning_advice} />
            <ResearchList title="面试策略" items={research.interview_strategy} />
            <ResearchList title="简历修改建议" items={research.resume_rewrite_suggestions ?? []} />
          </div>
          <div className="cover-letter-box">
            <div className="item-title">
              <strong>求职信草稿</strong>
              <span>{validationLabel(research)}</span>
            </div>
            <p>{research.cover_letter_draft || "暂无求职信草稿"}</p>
          </div>
          {research.sources.length > 0 && (
            <div className="source-list">
              <h3>资料来源</h3>
              {research.sources.map((source) => (
                <a key={source.url} href={source.url} target="_blank" rel="noreferrer">
                  <span>{source.title}</span>
                  <ExternalLink size={14} />
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ResearchList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="research-list">
      <strong>{title}</strong>
      {items.length === 0 && <span className="muted">暂无</span>}
      {items.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function validationLabel(research: JobResearchResponse) {
  if (research.llm_json_repaired) {
    return "JSON 已自动修复";
  }
  if (research.llm_validation_status === "validated") {
    return "JSON 校验通过";
  }
  if (research.llm_validation_status === "fallback") {
    return "Fallback 生成";
  }
  return "本地建议";
}

function sourceLabel(source: string) {
  if (source === "resume") {
    return "简历";
  }
  if (source === "supplemental_materials") {
    return "补充材料";
  }
  return source;
}

function modeLabel(config: AppConfig) {
  if (!config.llm_enabled) {
    return "本地模式";
  }
  if (config.llm_provider === "deepseek") {
    return "DeepSeek API";
  }
  if (config.llm_provider === "openai") {
    return "OpenAI API";
  }
  return `${config.llm_provider} API`;
}

function parseMethodLabel(method: string) {
  if (method === "text_file") {
    return "文本文件";
  }
  if (method === "pdf_text_layer") {
    return "PDF 文本层";
  }
  if (method === "pdf_layout_text") {
    return "PDF 版面感知提取";
  }
  if (method === "ocr_api") {
    return "OCR API";
  }
  if (method === "ocr_api_llm_cleaned") {
    return "OCR API + LLM 清洗";
  }
  if (method === "pdf_text_layer_insufficient") {
    return "PDF 文本层不足";
  }
  return method;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function ResultBlock({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "good" | "warn";
}) {
  return (
    <section>
      <h2>{title}</h2>
      <div className="chips">
        {items.length === 0 && <span className="muted">暂未识别</span>}
        {items.map((item) => (
          <span key={item} className={`chip ${tone}`}>
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
