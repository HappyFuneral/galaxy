import React, { useMemo } from "react";
import { View, StyleSheet, Dimensions } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { Theme } from "../theme";

const { width, height } = Dimensions.get("window");

function Starfield() {
  const stars = useMemo(() => {
    const n = 120;
    return new Array(n).fill(0).map((_, i) => {
      const x = Math.random() * width;
      const y = Math.random() * height;
      const s = Math.random() * 2.2 + 0.5;
      const a = Math.random() * 0.75 + 0.15;
      return { key: `s${i}`, x, y, s, a };
    });
  }, []);

  return (
    <View style={StyleSheet.absoluteFill}>
      {stars.map((st) => (
        <View
          key={st.key}
          style={{
            position: "absolute",
            left: st.x,
            top: st.y,
            width: st.s,
            height: st.s,
            borderRadius: 999,
            backgroundColor: `rgba(255,255,255,${st.a})`,
          }}
        />
      ))}
    </View>
  );
}

export function GalaxyBackground({ children }: { children: React.ReactNode }) {
  return (
    <View style={styles.root}>
      <LinearGradient
        colors={[Theme.colors.bg0, Theme.colors.bg1, "#0B1027", "#130A2A"]}
        start={{ x: 0.1, y: 0.0 }}
        end={{ x: 0.9, y: 1.0 }}
        style={StyleSheet.absoluteFill}
      />
      <Starfield />
      <View style={[styles.blob, { left: -120, top: 40, backgroundColor: "rgba(155,92,255,0.18)" }]} />
      <View style={[styles.blob, { right: -140, top: 160, backgroundColor: "rgba(53,211,255,0.14)" }]} />
      <View style={[styles.blob, { left: -80, bottom: -40, backgroundColor: "rgba(255,79,216,0.12)" }]} />
      <LinearGradient
        colors={["rgba(0,0,0,0.0)", "rgba(0,0,0,0.35)", "rgba(0,0,0,0.55)"]}
        start={{ x: 0.5, y: 0.0 }}
        end={{ x: 0.5, y: 1.0 }}
        style={StyleSheet.absoluteFill}
      />
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: Theme.colors.bg0 },
  content: { flex: 1 },
  blob: {
    position: "absolute",
    width: 360,
    height: 360,
    borderRadius: 360,
  } as any,
});
