import QtQuick

QtObject {
    // Backgrounds
    readonly property color surface: "#212529"
    readonly property color surfaceDark: "#1a1d20"
    readonly property color surfaceCard: "#2a2f35"
    readonly property color surfaceCardHover: "#343a42"
    readonly property color surfaceElevated: "#39404b"

    // Borders
    readonly property color borderSubtle: "#495057"

    // Accent
    readonly property color accent: "#6366f1"
    readonly property color accentHover: "#4f46e5"
    readonly property color accentLight: "#818cf8"
    readonly property color accentBg: "#336366f1"

    // Status
    readonly property color danger: "#ef4444"
    readonly property color dangerHover: "#dc2626"
    readonly property color success: "#22c55e"
    readonly property color warning: "#f59e0b"

    // Text
    readonly property color textPrimary: "#e5e7eb"
    readonly property color textSecondary: "#9ca3af"
    readonly property color textMuted: "#6b7280"
    readonly property color textWhite: "#ffffff"

    // Sizes
    readonly property int sidebarWidth: 208
    readonly property int borderRadius: 8
    readonly property int borderRadiusSm: 6
    readonly property int spacing: 12
    readonly property int spacingSm: 8
    readonly property int spacingXs: 4
}
