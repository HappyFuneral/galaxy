import React, { useMemo, useState } from "react";
import { SafeAreaView, StyleSheet, Text, View, Pressable } from "react-native";
import { GalaxyBackground } from "./app/ui/GalaxyBackground";
import { Theme } from "./app/theme";
import { HomeScreen } from "./app/screens/HomeScreen";
import { JobsScreen } from "./app/screens/JobsScreen";
import { JobDetailScreen } from "./app/screens/JobDetailScreen";
import { ExportDetailScreen } from "./app/screens/ExportDetailScreen";

type Tab = "home" | "jobs" | "detail" | "export";

export default function App() {
  const [tab, setTab] = useState<Tab>("home");
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeExportId, setActiveExportId] = useState<string | null>(null);

  const title = useMemo(() => {
    if (tab === "home") return "Home";
    if (tab === "jobs") return "Jobs";
    if (tab === "detail") return "Job Detail";
    return "Export Detail";
  }, [tab]);

  return (
    <GalaxyBackground>
      <SafeAreaView style={styles.safe}>
        <View style={styles.topbar}>
          <Text style={styles.topTitle}>{title}</Text>
        </View>

        <View style={styles.body}>
          {tab === "home" ? (
            <HomeScreen
              onJobCreated={(id) => {
                setJobIds((prev) => [id, ...prev]);
                setTab("jobs");
              }}
            />
          ) : null}

          {tab === "jobs" ? (
            <JobsScreen
              jobIds={jobIds}
              onOpenJob={(id) => {
                setActiveJobId(id);
                setTab("detail");
              }}
            />
          ) : null}

          {tab === "detail" && activeJobId ? (
            <JobDetailScreen
              jobId={activeJobId}
              onOpenExport={(exportId) => {
                setActiveExportId(exportId);
                setTab("export");
              }}
            />
          ) : null}

          {tab === "export" && activeJobId && activeExportId ? (
            <ExportDetailScreen
              jobId={activeJobId}
              exportId={activeExportId}
              onBack={() => setTab("detail")}
            />
          ) : null}
        </View>

        <View style={styles.nav}>
          <NavBtn label="Home" active={tab === "home"} onPress={() => setTab("home")} />
          <NavBtn label="Jobs" active={tab === "jobs"} onPress={() => setTab("jobs")} />
          <NavBtn label="Detail" active={tab === "detail"} onPress={() => setTab("detail")} disabled={!activeJobId} />
          <NavBtn label="Export" active={tab === "export"} onPress={() => setTab("export")} disabled={!activeExportId} />
        </View>
      </SafeAreaView>
    </GalaxyBackground>
  );
}

function NavBtn({ label, active, onPress, disabled }: { label: string; active: boolean; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={disabled} style={[styles.navBtn, active && styles.navBtnActive, disabled && { opacity: 0.4 }]}>
      <Text style={[styles.navText, active && { color: Theme.colors.text }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  topbar: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 10,
  },
  topTitle: { color: Theme.colors.text, fontSize: 16, fontWeight: "800", opacity: 0.92 },
  body: { flex: 1 },
  nav: {
    flexDirection: "row",
    padding: 10,
    gap: 10,
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.10)",
    backgroundColor: "rgba(7,6,18,0.55)",
  },
  navBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.10)",
    backgroundColor: "rgba(255,255,255,0.06)",
  },
  navBtnActive: {
    borderColor: "rgba(155,92,255,0.40)",
    backgroundColor: "rgba(155,92,255,0.16)",
  },
  navText: { color: Theme.colors.muted, fontWeight: "800", fontSize: 12 },
});
