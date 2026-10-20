"use client";

import { useRouter } from "next/navigation";
import { Suspense, useRef, useState } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { useTeacherNavigation } from "@/components/teacher-navigation";
import { LogoutButton } from "@/components/logout-button";
import { api, ApiError } from "@/lib/api";

const ACCEPT = ".pdf,.pptx,.docx,.jpg,.png,.md,.txt";

function UploadHome() {
  const nav = useTeacherNavigation();
  const classId = nav.teachingClassId;
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasClasses = classId !== null;

  const reset = () => {
    setFile(null);
    setDescription("");
    setTags("");
    setProgress(null);
    setError("");
    setSuccess("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setError("");
      setSuccess("");
    }
  };

  const doUpload = async () => {
    if (!classId || !file) {
      setError("请选择班级和文件");
      return;
    }
    setUploading(true);
    setError("");
    setSuccess("");
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("class_id", String(classId));
    formData.append("description", description);
    formData.append("tags", tags);

    try {
      const res = await api.uploadMaterial(formData, (loaded, total) => {
        setProgress(Math.round((loaded / total) * 100));
      });
      setSuccess(`${res.message}（文件：${res.filename}，大小：${(res.file_size / 1024 / 1024).toFixed(2)}MB）`);
      reset();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "上传失败";
      setError(msg);
      setProgress(null);
    } finally {
      setUploading(false);
    }
  };

  const router = useRouter();

  return (
    <AppShell
      brandMark="T"
      subtitle="智能教学平台 · 教师端"
      navItems={nav.navItems}
      navHeader={nav.navHeader}
      navFoot="CampusClaw · 教师工作空间"
      active="upload"
      onNavigate={nav.onNavigate}
      headerRight={
        <>
          <button className="hdr-btn" onClick={() => router.push(nav.href("students", "teaching", classId))}>返回工作台</button>
          <LogoutButton />
        </>
      }
    >
      <div className="content" style={{ padding: 0, maxWidth: "none" }}>
        <div className="page-title"><h2>单科资料发布</h2><p>{nav.subjectName} · 直接发布学生讲义到当前任教班级。</p></div>
        <div className="card" style={{ padding: 20, marginBottom: 20 }}><p>带答案的教师版请先导入教研组资料，在组内预览无答案学生版后选择班级发布。</p><button className="btn-pill ghost" onClick={() => router.push("/teacher/library")}>进入教研组资料</button></div>

        {!hasClasses ? (
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <p className="hint" style={{ fontSize: 16 }}>暂无任教班级</p>
            <p className="hint" style={{ marginTop: 8 }}>您尚未被分配任教班级，请联系管理员处理。</p>
          </div>
        ) : (
          <div className="card" style={{ padding: 24 }}>
            <div style={{ marginBottom: 16 }}>
              <span className="class-pill">{nav.subjectName} · 班级 {classId}</span>
              <button className="hdr-btn" onClick={() => router.push(nav.materialHref(classId, "teaching"))}>查看已发布资料</button>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label className="hint" style={{ display: "block", marginBottom: 8 }}>选择文件：</label>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPT}
                onChange={handleFileChange}
                disabled={uploading}
                style={{ width: "100%" }}
              />
              <p className="hint" style={{ marginTop: 4, fontSize: 12 }}>
                允许格式：PDF / PPTX / DOCX / JPG / PNG / MD / TXT，单文件 ≤ 50MB
              </p>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label className="hint" style={{ display: "block", marginBottom: 8 }}>描述（可选）：</label>
              <input
                className="input"
                placeholder="例如：第三章 代数方程练习"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={uploading}
              />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label className="hint" style={{ display: "block", marginBottom: 8 }}>标签（逗号分隔，可选）：</label>
              <input
                className="input"
                placeholder="例如：数学,代数,方程"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                disabled={uploading}
              />
            </div>

            {progress !== null && progress > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div className="hint" style={{ marginBottom: 4 }}>上传进度：{progress}%</div>
                <div style={{ background: "#e5e7eb", borderRadius: 4, height: 8, overflow: "hidden" }}>
                  <div style={{ width: `${progress}%`, background: "var(--brand)", height: "100%", transition: "width 0.2s" }} />
                </div>
              </div>
            )}

            {error && (
              <div className="error" style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>{error}</span>
                <button
                  className="btn"
                  style={{ width: "auto", padding: "4px 12px", fontSize: 13 }}
                  onClick={doUpload}
                  disabled={uploading || !file}
                >
                  重试
                </button>
              </div>
            )}

            {success && (
              <div style={{ background: "#d1fae5", color: "#065f46", padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
                {success}
              </div>
            )}

            <button
              className="btn"
              onClick={doUpload}
              disabled={uploading || !file || !classId}
            >
              {uploading ? "上传中…" : "上传"}
            </button>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default function UploadPage() {
  return (
    <AuthGate>
      <Suspense fallback={<div className="centered">加载中…</div>}><UploadHome /></Suspense>
    </AuthGate>
  );
}
