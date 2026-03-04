# Mobile V1.7.1 – Export Detail + Preview

Changes:
- axios removed (fixes Expo Hermes "crypto" error)
- JobsScreen imports View (fixes "Property 'View' doesn't exist")
- New ExportDetailScreen with sliders:
  - highlight opacity
  - glow sigma
  - fade duration
  - bgm gain
  - Preview button calls backend preview endpoint
- JobDetailScreen: per-export "Edit / Preview" button navigates to ExportDetailScreen

Requirements:
- Install slider:
  - npx expo install @react-native-community/slider
- expo-av is already standard with Expo SDK; if missing:
  - npx expo install expo-av
