import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Theme } from "../theme";

export function Card({ title, children }: { title?: string; children: React.ReactNode }) {
  return (
    <View style={styles.card}>
      {title ? <Text style={styles.cardTitle}>{title}</Text> : null}
      {children}
    </View>
  );
}

export function NeonButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable onPress={onPress} disabled={disabled} style={({ pressed }) => [styles.btnWrap, pressed && { opacity: 0.92 }, disabled && { opacity: 0.5 }]}>
      <LinearGradient
        colors={[Theme.colors.purple2, Theme.colors.pink, Theme.colors.cyan]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.btn}
      >
        <Text style={styles.btnText}>{label}</Text>
      </LinearGradient>
    </Pressable>
  );
}

export function Pill({ text, tone }: { text: string; tone?: "ok" | "warn" | "bad" | "info" }) {
  const bg =
    tone === "ok" ? "rgba(44,230,165,0.18)"
    : tone === "warn" ? "rgba(255,211,108,0.16)"
    : tone === "bad" ? "rgba(255,77,109,0.16)"
    : "rgba(155,92,255,0.16)";
  const border =
    tone === "ok" ? "rgba(44,230,165,0.28)"
    : tone === "warn" ? "rgba(255,211,108,0.28)"
    : tone === "bad" ? "rgba(255,77,109,0.28)"
    : "rgba(155,92,255,0.28)";
  return (
    <View style={[styles.pill, { backgroundColor: bg, borderColor: border }]}>
      <Text style={styles.pillText}>{text}</Text>
    </View>
  );
}

export function Row({ left, right }: { left: string; right: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLeft}>{left}</Text>
      <Text style={styles.rowRight}>{right}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Theme.colors.card,
    borderColor: Theme.colors.border,
    borderWidth: 1,
    borderRadius: Theme.radius.xl,
    padding: 16,
    marginBottom: 14,
    ...Theme.shadow.card,
  },
  cardTitle: {
    color: Theme.colors.text,
    fontSize: 14,
    letterSpacing: 0.4,
    marginBottom: 10,
    opacity: 0.9,
  },
  btnWrap: { marginTop: 10 },
  btn: {
    borderRadius: Theme.radius.lg,
    paddingVertical: 14,
    alignItems: "center",
  },
  btnText: { color: "#0B0716", fontWeight: "800", fontSize: 15, letterSpacing: 0.3 },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    alignSelf: "flex-start",
  },
  pillText: { color: Theme.colors.text, fontSize: 12, opacity: 0.9 },
  row: { flexDirection: "row", justifyContent: "space-between", marginVertical: 4 },
  rowLeft: { color: Theme.colors.muted, fontSize: 13 },
  rowRight: { color: Theme.colors.text, fontSize: 13, maxWidth: "58%", textAlign: "right" },
});
