import React, { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, Pressable, View } from "react-native";
import { Theme } from "../theme";
import { Card, Pill, Row } from "../ui/components";
import { getJob, Job } from "../api";

export function JobsScreen({ jobIds, onOpenJob }: { jobIds: string[]; onOpenJob: (jobId: string) => void }) {
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((x) => x + 1), 1500);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      for (const id of jobIds.slice().reverse()) {
        try {
          const j = await getJob(id);
          if (!cancelled) setJobs((prev) => ({ ...prev, [id]: j }));
        } catch {}
      }
    }
    load();
    return () => { cancelled = true; };
  }, [jobIds, tick]);

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <Text style={styles.h1}>Jobs</Text>
      <Text style={styles.sub}>Státusz, progress, és ha kész: részletek + exportok.</Text>

      {jobIds.length === 0 ? (
        <Card>
          <Text style={{ color: Theme.colors.muted }}>
            Még nincs job. Menj a Home-ra és indíts egyet.
          </Text>
        </Card>
      ) : null}

      {jobIds.slice().reverse().map((id) => {
        const j = jobs[id];
        const tone =
          j?.status === "done" ? "ok" :
          j?.status === "failed" ? "bad" :
          j?.status === "running" ? "warn" : "info";

        return (
          <Pressable key={id} onPress={() => onOpenJob(id)}>
            <Card title={id.slice(0, 8) + "…"}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <Pill text={j ? j.status.toUpperCase() : "LOADING"} tone={tone as any} />
                <Text style={{ color: Theme.colors.muted, fontSize: 12 }}>
                  {j ? Math.round((j.progress ?? 0) * 100) + "%" : ""}
                </Text>
              </View>

              <Row left="Platform" right={j?.platform ?? "-"} />
              <Row left="Stage" right={j?.stage ?? "-"} />
              <Row left="Captions" right={j?.captions ? "on" : "off"} />
              <Row left="Burn-in" right={(j as any)?.burn_in ? "on" : "off"} />
              <Row left="Speaker focus" right={(j as any)?.speaker_focus ? "on" : "off"} />

              {j?.error ? (
                <Text style={{ color: Theme.colors.red, marginTop: 10 }}>{j.error}</Text>
              ) : null}
            </Card>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 18, paddingTop: 26, paddingBottom: 40 },
  h1: { color: Theme.colors.text, fontSize: 28, fontWeight: "900" },
  sub: { color: Theme.colors.muted, marginTop: 6, marginBottom: 18, lineHeight: 18 },
});
