import React, { useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertCircle,
  BadgeCheck,
  BriefcaseBusiness,
  FileText,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Sparkles,
  UploadCloud
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [resume, setResume] = useState(null);
  const [match, setMatch] = useState(null);
  const [jobDescription, setJobDescription] = useState(sampleJD);
  const [manualText, setManualText] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  const profile = resume?.profile;
  const scoreTone = useMemo(() => {
    if (!match) return "idle";
    if (match.score >= 80) return "strong";
    if (match.score >= 60) return "medium";
    return "weak";
  }, [match]);

  async function uploadResume(file) {
    if (!file) return;
    setBusy("parse");
    setError("");
    setMatch(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const data = await request("/api/resumes", { method: "POST", body: form });
      setResume(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function parseText() {
    if (!manualText.trim()) return;
    setBusy("parse");
    setError("");
    setMatch(null);
    try {
      const data = await request("/api/resumes/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: manualText })
      });
      setResume(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function runMatch() {
    if (!resume || !jobDescription.trim()) return;
    setBusy("match");
    setError("");
    try {
      const data = await request("/api/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_id: resume.resume_id, job_description: jobDescription })
      });
      setMatch(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <main className="shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="brand">
            <span className="brandMark"><Sparkles size={18} /></span>
            <div>
              <h1>智能简历分析系统</h1>
              <p>PDF 解析、信息抽取、岗位匹配</p>
            </div>
          </div>

          <label className="dropzone">
            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => uploadResume(event.target.files?.[0])}
            />
            <UploadCloud size={28} />
            <span>上传 PDF 简历</span>
            <small>{busy === "parse" ? "正在解析..." : "支持单个多页 PDF"}</small>
          </label>

          <div className="manual">
            <label>文本解析</label>
            <textarea
              value={manualText}
              onChange={(event) => setManualText(event.target.value)}
              placeholder="粘贴简历文本用于快速演示"
            />
            <button className="ghostBtn" onClick={parseText} disabled={busy === "parse" || !manualText.trim()}>
              {busy === "parse" ? <Loader2 className="spin" size={16} /> : <FileText size={16} />}
              解析文本
            </button>
          </div>
        </aside>

        <section className="content">
          <div className="topbar">
            <div>
              <p className="eyebrow">Recruitment Console</p>
              <h2>候选人初筛工作台</h2>
            </div>
            <button className="primaryBtn" onClick={runMatch} disabled={!resume || busy === "match"}>
              {busy === "match" ? <Loader2 className="spin" size={17} /> : <BriefcaseBusiness size={17} />}
              计算匹配度
            </button>
          </div>

          {error && (
            <div className="alert">
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          <div className="grid">
            <section className="panel resumePanel">
              <div className="panelHead">
                <h3>解析结果</h3>
                {resume?.cache_hit && <span className="cache">Cache Hit</span>}
              </div>

              {!resume ? (
                <EmptyState />
              ) : (
                <>
                  <div className="identity">
                    <div>
                      <span className="avatar">{(profile?.basic?.name || "候")[0]}</span>
                    </div>
                    <div>
                      <h4>{profile?.basic?.name || "未识别姓名"}</h4>
                      <p>{profile?.job_intention || "求职意向待确认"}</p>
                    </div>
                  </div>

                  <div className="facts">
                    <Fact icon={<Phone size={15} />} text={profile?.basic?.phone || "电话未识别"} />
                    <Fact icon={<Mail size={15} />} text={profile?.basic?.email || "邮箱未识别"} />
                    <Fact icon={<MapPin size={15} />} text={profile?.basic?.address || "地址未识别"} />
                  </div>

                  <div className="metrics">
                    <Metric label="工作年限" value={profile?.years_of_experience ? `${profile.years_of_experience} 年` : "待确认"} />
                    <Metric label="期望薪资" value={profile?.expected_salary || "待确认"} />
                    <Metric label="学历记录" value={`${profile?.education?.length || 0} 条`} />
                  </div>

                  <TagList title="技能关键词" items={profile?.skills || []} />
                  <TextBlock title="简历摘要" text={profile?.summary || resume.text?.slice(0, 180)} />
                </>
              )}
            </section>

            <section className="panel jdPanel">
              <div className="panelHead">
                <h3>岗位需求</h3>
                <span>{jobDescription.length} 字</span>
              </div>
              <textarea
                className="jdInput"
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
              />
            </section>

            <section className={`panel scorePanel ${scoreTone}`}>
              <div className="panelHead">
                <h3>匹配评分</h3>
                {match?.cache_hit && <span className="cache">Cache Hit</span>}
              </div>

              {!match ? (
                <div className="scoreEmpty">解析简历后计算岗位匹配度</div>
              ) : (
                <>
                  <div className="scoreDial">
                    <span>{match.score}</span>
                    <small>/100</small>
                  </div>
                  <p className="comment">{match.ai_comment}</p>
                  <div className="bars">
                    <Bar label="技能匹配" value={match.breakdown.skill_match} />
                    <Bar label="经验相关" value={match.breakdown.experience_relevance} />
                    <Bar label="学历匹配" value={match.breakdown.education_match} />
                    <Bar label="关键词覆盖" value={match.breakdown.keyword_coverage} />
                  </div>
                  <TagList title="命中关键词" items={match.matched_keywords} positive />
                  <TagList title="待确认关键词" items={match.missing_keywords} />
                </>
              )}
            </section>
          </div>
        </section>
      </section>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="empty">
      <BadgeCheck size={34} />
      <p>等待简历输入</p>
      <span>上传 PDF 或粘贴文本后展示结构化结果</span>
    </div>
  );
}

function Fact({ icon, text }) {
  return (
    <div className="fact">
      {icon}
      <span>{text}</span>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TagList({ title, items, positive = false }) {
  const visible = items?.filter(Boolean).slice(0, 18) || [];
  return (
    <div className="tagGroup">
      <h5>{title}</h5>
      <div className="tags">
        {visible.length ? visible.map((item) => <span className={positive ? "tag positive" : "tag"} key={item}>{item}</span>) : <small>暂无</small>}
      </div>
    </div>
  );
}

function TextBlock({ title, text }) {
  return (
    <div className="textBlock">
      <h5>{title}</h5>
      <p>{text}</p>
    </div>
  );
}

function Bar({ label, value }) {
  return (
    <div className="barRow">
      <span>{label}</span>
      <div className="barTrack"><i style={{ width: `${Math.max(4, Math.min(100, value))}%` }} /></div>
      <strong>{value}</strong>
    </div>
  );
}

async function request(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    throw new Error(data?.detail || data || "请求失败");
  }
  return data;
}

const sampleJD = `招聘 Python 后端工程师：
1. 3 年以上后端开发经验，熟悉 Python、FastAPI 或 Django；
2. 熟悉 MySQL、Redis、Docker，具备云服务部署经验；
3. 有大模型应用、RAG、NLP 或简历解析项目经验优先；
4. 能独立完成接口设计、性能优化和线上问题排查。`;

createRoot(document.getElementById("root")).render(<App />);
