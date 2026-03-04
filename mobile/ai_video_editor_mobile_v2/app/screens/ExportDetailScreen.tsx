import React, { useEffect, useMemo, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View, Switch } from "react-native";
import Slider from "@react-native-community/slider";
import { Video } from "expo-av";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import { Theme } from "../theme";
import { Card, NeonButton, Pill, Row } from "../ui/components";
import { absoluteUrl, getExportRecipe, patchExportRecipe, previewExport, reexportHQ } from "../api";

type Props = { jobId: string; exportId: string; onBack: () => void; };

async function downloadAndShare(url: string | undefined, filename: string | undefined) {
  try {
    const dir = FileSystem.cacheDirectory ?? FileSystem.documentDirectory ?? "";
    const dest = dir + filename;
    const res = await FileSystem.downloadAsync(url, dest);
    if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(res.uri);
    else Alert.alert("Letöltve", res.uri);
  } catch (e: any) {
    Alert.alert("Letöltési hiba", e?.message ?? "Ismeretlen hiba");
  }
}

export function ExportDetailScreen({ jobId, exportId, onBack }: Props) {
  const [recipe, setRecipe] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reexp, setReexp] = useState<{ url: string; name: string } | null>(null);

  const [opacity, setOpacity] = useState(0.14);
  const [sigma, setSigma] = useState(1.1);
  const [fade, setFade] = useState(0.30);
  const [bgmGain, setBgmGain] = useState(-18);

  // NEW
  const [tintEnabled, setTintEnabled] = useState(false);
  const [tintStrength, setTintStrength] = useState(0.12);

  const [vignetteEnabled, setVignetteEnabled] = useState(false);
  const [vignetteStrength, setVignetteStrength] = useState(0.35);

  const [grainEnabled, setGrainEnabled] = useState(false);
  const [grainStrength, setGrainStrength] = useState(0.08);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await getExportRecipe(jobId, exportId);
        if (cancelled) return;
        setRecipe(r);

        const ov = r?.overrides ?? {};
        const glow = ov?.postprocess?.highlight?.glow ?? {};
        if (typeof glow.opacity === "number") setOpacity(glow.opacity);
        if (typeof glow.sigma === "number") setSigma(glow.sigma);

        const f = ov?.postprocess?.fade ?? {};
        if (typeof f.duration_s === "number") setFade(f.duration_s);

        const am = ov?.audio_mix?.bgm ?? {};
        if (typeof am.base_gain_db === "number") setBgmGain(am.base_gain_db);

        const ct = ov?.postprocess?.color_tint ?? {};
        if (typeof ct.enabled === "boolean") setTintEnabled(ct.enabled);
        if (typeof ct.strength === "number") setTintStrength(ct.strength);

        const vg = ov?.postprocess?.vignette ?? {};
        if (typeof vg.enabled === "boolean") setVignetteEnabled(vg.enabled);
        if (typeof vg.strength === "number") setVignetteStrength(vg.strength);

        const gr = ov?.postprocess?.film_grain ?? {};
        if (typeof gr.enabled === "boolean") setGrainEnabled(gr.enabled);
        if (typeof gr.strength === "number") setGrainStrength(gr.strength);
      } catch (e: any) {
        Alert.alert("Hiba", e?.message ?? "Nem sikerült betölteni a recipe-t");
      }
    })();
    return () => { cancelled = true; };
  }, [jobId, exportId]);

  const overrides = useMemo(() => {
    const base: any = {
      postprocess: {
        fade: { enabled: true, duration_s: fade },
        highlight: { enabled: true, glow: { enabled: true, opacity, sigma } },

        color_tint: { enabled: tintEnabled, type: "purple", strength: tintStrength },
        vignette: { enabled: vignetteEnabled, strength: vignetteStrength },
        film_grain: { enabled: grainEnabled, strength: grainStrength },
      },
      audio_mix: { bgm: { base_gain_db: bgmGain } },
    };

    const aw = recipe?.overrides?.active_windows ?? recipe?.active_windows ?? null;
    if (aw) base.active_windows = aw;

    return base;
  }, [opacity, sigma, fade, bgmGain, tintEnabled, tintStrength, vignetteEnabled, vignetteStrength, grainEnabled, grainStrength, recipe]);

  async function runPreview() {
    setLoading(true);
    try {
      const res = await previewExport(jobId, exportId, { seconds: 6, size_w: 540, size_h: 960, overrides });
      setPreviewUrl(absoluteUrl(res.preview_url));
    } catch (e: any) {
      Alert.alert("Preview hiba", e?.message ?? "Nem sikerült preview-t renderelni");
    } finally {
      setLoading(false);
    }
  }

  async function saveRecipe() {
    setSaving(true);
    try {
      const updated = await patchExportRecipe(jobId, exportId, overrides);
      setRecipe(updated);
      Alert.alert("Mentve", "A beállításokat elmentettem a recipe-be.");
    } catch (e: any) {
      Alert.alert("Mentés hiba", e?.message ?? "Nem sikerült menteni");
    } finally {
      setSaving(false);
    }
  }

  async function reexport() {
    setLoading(true);
    try {
      const res = await reexportHQ(jobId, exportId, overrides);
      const url = absoluteUrl(res.file_url);
      const name = res.new_export_id + ".mp4";
      setReexp({ url, name });
      Alert.alert("Kész", "Új HQ export elkészült. Le tudod tölteni / megosztani.");
    } catch (e: any) {
      Alert.alert("Re-export hiba", e?.message ?? "Nem sikerült re-exportálni");
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.wrap}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <Text style={styles.h1}>Export {exportId}</Text>
        <NeonButton label="Back" onPress={onBack} />
      </View>
      <Text style={styles.sub}>Slider → Preview → Save → HQ Re-export</Text>

      <Card title="Recipe">
        <Row left="Platform" right={recipe?.platform ?? "-"} />
        <Row left="Input" right={(recipe?.input_video ?? "").split("/").pop() || "-"} />
        <Row left="Segment" right={recipe?.segment ? `${recipe.segment.start}s → ${recipe.segment.end}s` : "-"} />
      </Card>

      <Card title="Tuning">
        <Text style={styles.label}>Highlight opacity: {opacity.toFixed(2)}</Text>
        <Slider minimumValue={0.0} maximumValue={0.30} step={0.01} value={opacity} onValueChange={setOpacity} minimumTrackTintColor={Theme.colors.purple} />

        <Text style={styles.label}>Glow sigma: {sigma.toFixed(2)}</Text>
        <Slider minimumValue={0.3} maximumValue={2.5} step={0.05} value={sigma} onValueChange={setSigma} minimumTrackTintColor={Theme.colors.purple} />

        <Text style={styles.label}>Fade duration: {fade.toFixed(2)}s</Text>
        <Slider minimumValue={0.05} maximumValue={0.7} step={0.05} value={fade} onValueChange={setFade} minimumTrackTintColor={Theme.colors.purple} />

        <Text style={styles.label}>BGM gain: {bgmGain.toFixed(0)} dB</Text>
        <Slider minimumValue={-32} maximumValue={-6} step={1} value={bgmGain} onValueChange={setBgmGain} minimumTrackTintColor={Theme.colors.purple} />

        <View style={styles.sep} />

        <View style={styles.switchRow}>
          <Text style={styles.label}>Purple tint</Text>
          <Switch value={tintEnabled} onValueChange={setTintEnabled} trackColor={{ true: Theme.colors.purple, false: "#333" }} />
        </View>
        <Text style={styles.small}>Strength: {tintStrength.toFixed(2)}</Text>
        <Slider disabled={!tintEnabled} minimumValue={0.0} maximumValue={0.35} step={0.01} value={tintStrength} onValueChange={setTintStrength} minimumTrackTintColor={Theme.colors.purple} />

        <View style={styles.switchRow}>
          <Text style={styles.label}>Vignette</Text>
          <Switch value={vignetteEnabled} onValueChange={setVignetteEnabled} trackColor={{ true: Theme.colors.purple, false: "#333" }} />
        </View>
        <Text style={styles.small}>Strength: {vignetteStrength.toFixed(2)}</Text>
        <Slider disabled={!vignetteEnabled} minimumValue={0.0} maximumValue={1.0} step={0.05} value={vignetteStrength} onValueChange={setVignetteStrength} minimumTrackTintColor={Theme.colors.purple} />

        <View style={styles.switchRow}>
          <Text style={styles.label}>Film grain</Text>
          <Switch value={grainEnabled} onValueChange={setGrainEnabled} trackColor={{ true: Theme.colors.purple, false: "#333" }} />
        </View>
        <Text style={styles.small}>Strength: {grainStrength.toFixed(2)}</Text>
        <Slider disabled={!grainEnabled} minimumValue={0.0} maximumValue={0.25} step={0.01} value={grainStrength} onValueChange={setGrainStrength} minimumTrackTintColor={Theme.colors.purple} />

        <View style={{ height: 14 }} />
        <NeonButton label={loading ? "Rendering…" : "Preview (6s)"} onPress={runPreview} />
        <View style={{ height: 10 }} />
        <NeonButton label={saving ? "Saving…" : "Save settings"} onPress={saveRecipe} />
        <View style={{ height: 10 }} />
        <NeonButton label={loading ? "Working…" : "HQ Re-export"} onPress={reexport} />
      </Card>

      <Card title="Preview">
        {previewUrl ? (
          <>
            <Pill text="READY" tone="ok" />
            <View style={{ height: 14 }} />
            <Video source={{ uri: previewUrl }} style={{ width: "100%", height: 420, borderRadius: 18, backgroundColor: "rgba(0,0,0,0.35)" }} useNativeControls resizeMode="contain" shouldPlay />
          </>
        ) : (
          <Text style={{ color: Theme.colors.muted }}>Nyomj Preview-t.</Text>
        )}
      </Card>

      <Card title="HQ Re-export">
        {reexp ? (
          <>
            <Pill text="DONE" tone="ok" />
            <View style={{ height: 12 }} />
            <Text style={{ color: Theme.colors.text, fontWeight: "800" }}>{reexp.name}</Text>
            <View style={{ height: 10 }} />
            <NeonButton label="Download / Share" onPress={() => downloadAndShare(reexp?.url, reexp?.name)} />
          </>
        ) : (
          <Text style={{ color: Theme.colors.muted }}>Ha kész a re-export, itt lesz.</Text>
        )}
      </Card>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { padding: 18, paddingTop: 26, paddingBottom: 40 },
  h1: { color: Theme.colors.text, fontSize: 20, fontWeight: "900" },
  sub: { color: Theme.colors.muted, marginTop: 6, marginBottom: 18, lineHeight: 18 },
  label: { color: Theme.colors.text, marginTop: 12, marginBottom: 8, fontWeight: "800" },
  small: { color: Theme.colors.muted, marginTop: 8, fontSize: 11 },
  sep: { height: 1, backgroundColor: "rgba(255,255,255,0.08)", marginTop: 16, marginBottom: 10 },
  switchRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 6 },
});
