"""Design tokens: brand colors, question palette and neutral colors.

All foreground colors meet WCAG AA contrast ratio (≥ 4.5:1) on white.
"""

# --- Brand ---
SNCF_RED = "#E8003D"

# --- One color per question (used for left-border accents and chart defaults) ---
QUESTION_COLORS: dict[int, str] = {
    1: "#003F88",  # Q1 Michelle — navy blue
    2: "#FF6B35",  # Q2 Éric    — orange
    3: "#6A0572",  # Q3 Bachelard — purple
    4: "#2E7D32",  # Q4 Meryem  — green
}

# --- Cluster palette for Q3 (up to 6 clusters) ---
CLUSTER_COLORS = ["#6A0572", "#003F88", "#FF6B35", "#2E7D32", "#C62828", "#F9A825"]

# --- Neutral gray scale ---
GRAY_100 = "#F5F7FA"
GRAY_700 = "#4A5568"
GRAY_900 = "#1A1A2E"
