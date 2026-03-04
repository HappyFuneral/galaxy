
import { useEffect, useMemo, useState } from "react";

const API = "http://localhost:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [platform, setPlatform] = useState("tiktok");
  const [exportClips, setExportClips] = useState(true);

  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const progressPct = useMemo(() => Math.round(((job?.progress || 0) * 100)), [job]);

  async function uploadAndStart() {
    setError(null);
    setResult(null);
    setJob(null);
    setJobId(null);
    if (!file) return;
    setBusy(true);

    try {
      const form = new FormData();
      form.append("file", file);

      const upRes = await fetch(`${API}/upload`, { method: "POST", body: form });
      const up = await upRes.json();
      if (!upRes.ok) throw new Error(up.error || "Upload failed");

      const jobRes = await fetch(
        `${API}/jobs?video_id=${encodeURIComponent(up.video_id)}&platform=${encodeURIComponent(platform)}&export=${exportClips}`,
        { method: "POST" }
      );
      const jd = await jobRes.json();
      if (!jobRes.ok) throw new Error(jd.error || "Job start failed");

      setJobId(jd.job_id);
    } catch (e) {
      setError(String(e.message || e));
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${jobId}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Job fetch failed");
        if (cancelled) return;
        setJob(data);

        if (data.status === "done") {
          clearInterval(interval);
          const rRes = await fetch(`${API}/jobs/${jobId}/result`);
          const rData = await rRes.json();
          if (!rRes.ok) throw new Error(rData.error || "Result fetch failed");
          setResult(rData);
          setBusy(false);
        } else if (data.status === "failed") {
          clearInterval(interval);
          setError(data.error || "Job failed");
          setBusy(false);
        }
      } catch (e) {
        if (!cancelled) {
          setError(String(e.message || e));
          setBusy(false);
        }
      }
    }, 800);

    return () => { cancelled = true; clearInterval(interval); };
  }, [jobId]);

  return (
    <div style={{ padding: 24, maxWidth: 980, margin: "0 auto", fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700 }}>AI Video Editor (Complete V1)</h1>

      <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16, marginTop: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />

          <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="tiktok">TikTok</option>
            <option value="shorts">YouTube Shorts</option>
            <option value="reels">Instagram Reels</option>
          </select>

          <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={exportClips} onChange={(e) => setExportClips(e.target.checked)} />
            Export klipek (ffmpeg)
          </label>

          <button onClick={uploadAndStart} disabled={!file || busy} style={{ padding: "8px 12px" }}>
            {busy ? "Fut..." : "Upload + Analyze"}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: 12, padding: 10, border: "1px solid #f3b0b0", background: "#fff0f0", borderRadius: 8 }}>
            <b>Hiba:</b> {error}
          </div>
        )}

        {job && (
          <div style={{ marginTop: 12, padding: 10, border: "1px solid #ddd", borderRadius: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <b>Job: {job.status}</b>
              <span>{progressPct}%</span>
            </div>
            <div style={{ fontSize: 12, marginTop: 6 }}>Stage: {job.stage}</div>
            <div style={{ height: 8, background: "#eee", borderRadius: 6, overflow: "hidden", marginTop: 8 }}>
              <div style={{ height: 8, width: `${progressPct}%`, background: "#222" }} />
            </div>
            <div style={{ fontSize: 11, marginTop: 6, opacity: 0.7 }}>Job ID: {job.job_id}</div>
          </div>
        )}
      </div>

      {result && (
        <div style={{ marginTop: 18, display: "grid", gap: 12 }}>
          {result.fallback_used ? (
            <div style={{border:"1px solid #f0c36d", background:"#fff8e6", padding:12, borderRadius:10}}>
              <b>Figyelem:</b> Nem volt küszöb feletti klip, ezért fallback top találatokat választottunk.
            </div>
          ) : null}

          <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16 }}>
            <b>Összegzés</b>
            <div style={{ fontSize: 13, marginTop: 6 }}>Hossz: {Math.round(result.duration_s)}s</div>
            <div style={{ fontSize: 13 }}>Vizsgált szegmensek: {result.segments_considered}</div>
          </div>

          <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16 }}>
            <b>Kiválasztott klipek</b>
            <div style={{ marginTop: 10, display: "grid", gap: 10 }}>
              {result.selected?.length ? result.selected.map((c, idx) => (
                <div key={idx} style={{ border: "1px solid #eee", borderRadius: 10, padding: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <b>#{idx+1} — {c.start.toFixed(1)}s → {c.end.toFixed(1)}s</b>
                    <span>Final: {c.final_score.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: 13, marginTop: 6 }}>
                    Scores: music {c.scores.music.toFixed(2)} | visual {c.scores.visual.toFixed(2)} | emotion {c.scores.emotion.toFixed(2)} | platform {c.scores.platform.toFixed(2)}
                  </div>
                  <div style={{ fontSize: 12, marginTop: 6, opacity: 0.85 }}>
                    Ajánlás: {Object.values(c.recommendations || {}).join(" | ") || "—"}
                  </div>

                  {exportClips && result.exports?.length ? (
                    (() => {
                      const exp = result.exports.find(e => Math.abs(e.start - c.start) < 0.01 && Math.abs(e.end - c.end) < 0.01);
                      return exp ? (
                        <div style={{ marginTop: 10 }}>
                          <a href={`${API}${exp.url}`} target="_blank" rel="noreferrer">Download MP4</a>
                        </div>
                      ) : <div style={{ marginTop: 10, fontSize: 12, opacity: 0.7 }}>Export fájl nem található ehhez a kliphez.</div>
                    })()
                  ) : (
                    <div style={{ marginTop: 10, fontSize: 12, opacity: 0.7 }}>Export nincs bekapcsolva.</div>
                  )}
                </div>
              )) : <div style={{ marginTop: 10 }}>Nincs kiválasztott klip.</div>}
            </div>
          </div>

          {result.exports?.length ? (
            <div style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16 }}>
              <b>Exportok</b>
              <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                {result.exports.map((e, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                    <div style={{ fontSize: 13 }}>{e.filename} — {e.start.toFixed(1)}s → {e.end.toFixed(1)}s</div>
                    <a href={`${API}${e.url}`} target="_blank" rel="noreferrer">Download</a>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <details style={{ border: "1px solid #ddd", borderRadius: 10, padding: 16 }}>
            <summary style={{ cursor: "pointer" }}><b>Debug: candidates</b></summary>
            <pre style={{ marginTop: 10, fontSize: 11, overflow: "auto" }}>{JSON.stringify(result.candidates, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
