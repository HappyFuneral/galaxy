import React, { useEffect, useMemo, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Theme } from "../theme";
import { Card, Pill, Row, NeonButton } from "../ui/components";
import { downloadUrl, getJob, getJobResult, Job, listExports } from "../api";

function formatScore(x: any): string {
  const n = typeof x === "number" ? x : Number(x);
  if (Number.isFinite(n)) return n.toFixed(3);
  return "-";
}

async function downloadAndShare(url: string, filename: string) {
  try {
    const dir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory ?? "";
    const dest = dir + filename;

    const res = await FileSystem.downloadAsync(url, dest);
    if (await Sharing.isAvailableAsync()) {
      await Sharing.shareAsync(res.uri);
    } else {
      Alert.alert("Letöltve", res.uri);
    }
  } catch (e: any) {
    Alert.alert("Letöltési hiba", e?.message ?? "Ismeretlen hiba");
  }
}

export function JobDetailScreen({ jobId, onOpenExport }: { jobId: string; onOpenExport: (exportId: string) => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [exportsList, setExportsList] = useState<{ export_id: string; video: string; recipe: string | null }[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 1500);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const j = await getJob(jobId);
        if (!cancelled) setJob(j);
        if (j.status === "done") {
          const r = await getJobResult(jobId);
          if (!cancelled) setResult(r);

          // also fetch exports list (recipe-based)
          try {
            const el = await listExports(jobId);
            if (!cancelled) setExportsList(el.exports || []);
          } catch {}
        }
      } catch {}
    }
    load();
    return () => { cancelled = true; };
  }, [jobId, tick]);

  const exports = (result?.exports ?? []) as any[];
  const selected = (result?.selected ?? []) as any[];

  const topSummary = useMemo(() => {
    if (!selected?.length) return null;
    const best = selected[0];
    return {
      start: best.start,
      end: best.end,
      score: best.final_score,
      decision: best.decision,
      scores: best.scores,
    };
  }, [selected]);

  const statusTone =
    job?.status === "done" ? "ok" :
    job?.status === "failed" ? "bad" :
    job?.status === "running" ? "warn" : "info";

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <Text style={styles.h1}>Job {jobId.slice(0, 8)}…</Text>
      <Text style={styles.sub}>Döntések, exportok, és a teljes JSON.</Text>

      <Card title="Státusz">
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <Pill text={(job?.status ?? "loading").toUpperCase()} tone={statusTone as any} />
          <Text style={{ color: Theme.colors.muted, fontSize: 12 }}>
            {job ? Math.round((job.progress ?? 0) * 100) + "%" : ""}
          </Text>
        </View>
        <View style={{ height: 10 }} />
        <Row left="Platform" right={job?.platform ?? "-"} />
        <Row left="Stage" right={job?.stage ?? "-"} />
        {job?.error ? <Text style={{ color: Theme.colors.red, marginTop: 10 }}>{job.error}</Text> : null}
      </Card>

      {topSummary ? (
        <Card title="Legjobb klip (összefoglaló)">
          <Row left="Decision" right={topSummary.decision} />
          <Row left="Final score" right={formatScore(topSummary.score)} />
          <Row left="Idő" right={`${topSummary.start}s → ${topSummary.end}s`} />
          <Text style={styles.small}>Részpontszámok:</Text>
          {Object.entries(topSummary.scores || {}).map(([k, v]) => (
            <Row key={k} left={k} right={formatScore(v)} />
          ))}
        </Card>
      ) : null}

      <Card title="Exports (letöltés / megosztás / edit)">
        {exports?.length ? (
          exports.map((ex: any, idx: number) => {
            const mp4Url = downloadUrl(jobId, ex.filename);
            const srtName = ex.srt ? String(ex.srt).split("/").pop() : null;
            const srtUrl = srtName ? downloadUrl(jobId, srtName) : null;

            // try best: use export_id from backend (added in v1.7.1); fallback to stem from filename
            const exportId = ex.export_id || String(ex.filename).replace(/\.mp4$/,"");

            return (
              <View key={idx} style={styles.item}>
                <Row left="File" right={ex.filename} />
                <Row left="Idő" right={`${ex.start}s → ${ex.end}s`} />
                <Row left="BGM" right={ex.bgm_used ? `ON (${ex.bgm_reason})` : `OFF (${ex.bgm_reason})`} />

                <NeonButton label="Edit / Preview" onPress={() => onOpenExport(exportId)} />
                <NeonButton label="MP4 letöltés / megosztás" onPress={() => downloadAndShare(mp4Url, ex.filename)} />
                {srtUrl ? (
                  <NeonButton label="SRT letöltés / megosztás" onPress={() => downloadAndShare(srtUrl, srtName || "captions.srt")} />
                ) : null}
              </View>
            );
          })
        ) : (
          <Text style={{ color: Theme.colors.muted }}>Nincs export (export=false vagy még fut).</Text>
        )}
      </Card>

      <Card title="Raw JSON (job/result)">
        {result ? (
          <Text selectable style={styles.json}>
            {JSON.stringify(result, null, 2)}
          </Text>
        ) : (
          <Text style={{ color: Theme.colors.muted }}>
            A JSON akkor jelenik meg, ha a job DONE.
          </Text>
        )}
      </Card>

      <View style={{ height: 30 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 18, paddingTop: 26, paddingBottom: 40 },
  h1: { color: Theme.colors.text, fontSize: 26, fontWeight: "900" },
  sub: { color: Theme.colors.muted, marginTop: 6, marginBottom: 18, lineHeight: 18 },
  small: { color: Theme.colors.muted, marginTop: 10, fontSize: 12 },
  item: {
    backgroundColor: Theme.colors.card2,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    padding: 12,
    borderRadius: Theme.radius.lg,
    marginBottom: 12,
  },
  json: { color: Theme.colors.text, fontSize: 11, lineHeight: 16, opacity: 0.92 },
});
