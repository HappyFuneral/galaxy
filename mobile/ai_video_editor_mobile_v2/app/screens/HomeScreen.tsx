import React, { useMemo, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View, Switch } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import { Theme } from "../theme";
import { Card, NeonButton, Pill, Row } from "../ui/components";
import { createJob, uploadBgm, uploadVideo } from "../api";

type Platform = "tiktok" | "reels" | "shorts" | "youtube";

export function HomeScreen({ onJobCreated }: { onJobCreated: (jobId: string) => void }) {
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [bgmUri, setBgmUri] = useState<string | null>(null);

  const [platform, setPlatform] = useState<Platform>("tiktok");
  const [captions, setCaptions] = useState(true);
  const [burnIn, setBurnIn] = useState(true);
  const [speakerFocus, setSpeakerFocus] = useState(true);
  const [exportOn, setExportOn] = useState(true);

  const [busy, setBusy] = useState(false);

  const platformPills = useMemo(() => ([
    { id: "tiktok", label: "TikTok" },
    { id: "reels", label: "Reels" },
    { id: "shorts", label: "Shorts" },
    { id: "youtube", label: "YouTube" },
  ] as const), []);

  async function pickVideo() {
    const res = await DocumentPicker.getDocumentAsync({ type: ["video/*"] });
    if (res.canceled) return;
    setVideoUri(res.assets[0].uri);
  }

  async function pickBgm() {
    const res = await DocumentPicker.getDocumentAsync({ type: ["audio/*"] });
    if (res.canceled) return;
    setBgmUri(res.assets[0].uri);
  }

  async function startJob() {
    if (!videoUri) {
      Alert.alert("Hiányzik a videó", "Válassz ki egy videót feltöltéshez.");
      return;
    }

    try {
      setBusy(true);

      const up = await uploadVideo(videoUri);

      let bgm_id: string | null = null;
      if (bgmUri) {
        const b = await uploadBgm(bgmUri);
        bgm_id = b.bgm_id;
      }

      const job = await createJob({
        video_id: up.video_id,
        platform,
        export: exportOn,
        bgm_id: bgm_id ?? undefined,
        captions,
        burn_in: burnIn,
        speaker_focus: speakerFocus,
      });

      onJobCreated(job.job_id);
      Alert.alert("Elindítva", "A feldolgozás elindult. Nézd a Jobs tabon!");
    } catch (e: any) {
      Alert.alert("Hiba", e?.message ?? "Ismeretlen hiba");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <Text style={styles.h1}>Galaxy Clips</Text>
      <Text style={styles.sub}>Feltöltés → döntések → exportok. Sötét, gyors, zenészbarát.</Text>

      <Card title="1) Input">
        <Row left="Videó" right={videoUri ? "kiválasztva" : "nincs"} />
        <NeonButton label={videoUri ? "Videó cseréje" : "Videó kiválasztása"} onPress={pickVideo} disabled={busy} />

        <View style={{ height: 12 }} />

        <Row left="Háttérzene (opcionális)" right={bgmUri ? "kiválasztva" : "nincs"} />
        <Text style={styles.small}>
          Automata: beszédnél mehet, ha gitár/zenélés aktív → OFF.
        </Text>
        <NeonButton label={bgmUri ? "BGM cseréje" : "BGM kiválasztása"} onPress={pickBgm} disabled={busy} />
      </Card>

      <Card title="2) Platform">
        <View style={styles.pillRow}>
          {platformPills.map((p) => (
            <View key={p.id} style={{ marginRight: 10, marginBottom: 10 }}>
              <Text onPress={() => setPlatform(p.id as Platform)}>
                <Pill text={p.label} tone={platform === p.id ? "ok" : "info"} />
              </Text>
            </View>
          ))}
        </View>
        <Text style={styles.small}>A platform befolyásolja a kivágást és a pontozást.</Text>
      </Card>

      <Card title="3) Extra opciók">
        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Export készítése</Text>
          <Switch value={exportOn} onValueChange={setExportOn} />
        </View>

        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Felirat (SRT)</Text>
          <Switch value={captions} onValueChange={setCaptions} />
        </View>

        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Burn-in felirat</Text>
          <Switch value={burnIn} onValueChange={setBurnIn} />
        </View>

        <View style={styles.switchRow}>
          <Text style={styles.switchText}>Speaker focus (face crop)</Text>
          <Switch value={speakerFocus} onValueChange={setSpeakerFocus} />
        </View>
      </Card>

      <Card title="4) Start">
        <NeonButton label={busy ? "Fut..." : "Job indítása"} onPress={startJob} disabled={busy} />
        <Text style={styles.small}>
          Tipp: a “speaker focus” akkor aktivál, ha elég beszéd + elég arc detekt van.
        </Text>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 18, paddingTop: 26, paddingBottom: 40 },
  h1: { color: Theme.colors.text, fontSize: 30, fontWeight: "900", letterSpacing: 0.3 },
  sub: { color: Theme.colors.muted, marginTop: 6, marginBottom: 18, lineHeight: 18 },
  small: { color: Theme.colors.muted, marginTop: 8, fontSize: 12, lineHeight: 16 },
  pillRow: { flexDirection: "row", flexWrap: "wrap", marginTop: 6 },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginVertical: 6,
  },
  switchText: { color: Theme.colors.text, fontSize: 14, opacity: 0.9 },
});
