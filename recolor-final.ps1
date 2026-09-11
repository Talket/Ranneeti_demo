# Usage:  .\recolor-final.ps1 index.html.bak index.html
# One-shot script: takes the ORIGINAL (untouched) file as input and
# writes out the fully-recolored final version using a modern cool-dark
# theme optimized for extended viewing (eye-friendly, no eye strain).
#
# NEW PALETTE: GitHub-inspired cool dark theme with vibrant accents
# - Dark foundation (#0d1117 body, #161b22 panels): reduces eye strain
# - Clean text (#e6edf3 primary): high contrast, easy to read
# - Vibrant entity colors: bright sky blue, emerald, magenta, purple
#   instead of dull warm tones
# - Coral-orange accent (#FF7B72): vibrant and eye-friendly for hours of viewing
# This creates a 60% dark / 40% light color balance that's comfortable
# for hours of viewing while maintaining visual interest and uniqueness.

param(
    [Parameter(Mandatory=$true)]
    [string]$SourcePath,
    [Parameter(Mandatory=$true)]
    [string]$OutputPath
)

if (-not (Test-Path $SourcePath)) {
    Write-Error "Source file not found: $SourcePath"
    exit 1
}

$content = Get-Content -Raw -LiteralPath $SourcePath

# --- Organization special-case (must run BEFORE the generic amber sweep) ---
$content = $content -creplace 'organization:"#F59E0B"', 'organization:"#0EA5E9"'
$content = $content -creplace 'label:"Organization",color:"#F59E0B"', 'label:"Organization",color:"#0EA5E9"'

# --- Uppercase hex (inline JS: icons, graph node/edge colors) ---
$content = $content -creplace '#3B82F6', '#58A6FF'   # accent -> bright sky blue (+ person icon)
$content = $content -creplace '#F59E0B', '#FF7B72'   # remaining amber/ai_suggested -> coral-orange (vibrant, eye-friendly)
$content = $content -creplace '#10B981', '#3FB950'   # location -> bright emerald
$content = $content -creplace '#9CA3AF', '#BC8EF6'   # vehicle icon -> soft purple
$content = $content -creplace '#818CF8', '#F85149'   # phone icon -> vibrant red-pink
$content = $content -creplace '#4B5563', '#3D444D'   # confirmed edge / legend line
$content = $content -creplace '#22262E', '#161B22'   # svg grid + node fill (panel)
$content = $content -creplace '#F9FAFB', '#E6EDF3'   # node label text (clean white)
$content = $content -creplace '#6B7280', '#8B949E'   # secondary svg text
$content = $content -creplace '#2C313A', '#1D262F'   # node badge fill (elevated)

# --- Lowercase hex (compiled Tailwind CSS) ---
$content = $content -creplace '#181b21', '#0d1117'   # canvas/body bg (cool dark)
$content = $content -creplace '#22262e', '#161b22'   # panel (cool dark)
$content = $content -creplace '#2c313a', '#1d262f'   # elevated (cool dark)
$content = $content -creplace '#374151', '#30363d'   # border (cool gray)
$content = $content -creplace '#4b5563', '#3d444d'   # scrollbar hover (cool gray)
$content = $content -creplace '#f9fafb', '#e6edf3'   # text-primary (clean white)
$content = $content -creplace '#9ca3af', '#8b949e'   # text-secondary / placeholder (cool gray)
$content = $content -creplace '#6b7280', '#6e7681'   # text-tertiary (medium gray)
$content = $content -creplace '#3b82f6', '#58a6ff'   # accent -> bright sky blue
$content = $content -creplace '#f59e0b', '#ff7b72'   # watch (vibrant coral-orange)
$content = $content -creplace '#10b981', '#3fb950'   # cleared (bright emerald)
$content = $content -creplace '#ef4444', '#da3633'   # critical (bright red)

# --- rgb(...) forms used for Tailwind's opacity-variable classes ---
$content = $content -creplace 'rgb\(24 27 33', 'rgb(13 17 23'
$content = $content -creplace 'rgb\(34 38 46', 'rgb(22 27 34'
$content = $content -creplace 'rgb\(44 49 58', 'rgb(29 38 47'
$content = $content -creplace 'rgb\(55 65 81', 'rgb(48 54 61'
$content = $content -creplace 'rgb\(249 250 251', 'rgb(230 237 243'
$content = $content -creplace 'rgb\(156 163 175', 'rgb(139 148 158'
$content = $content -creplace 'rgb\(107 114 128', 'rgb(110 118 129'
$content = $content -creplace 'rgb\(59 130 246', 'rgb(88 166 255'
$content = $content -creplace 'rgb\(245 158 11', 'rgb(255 123 114'
$content = $content -creplace 'rgb\(16 185 129', 'rgb(63 185 80'
$content = $content -creplace 'rgb\(239 68 68', 'rgb(218 54 51'

Set-Content -LiteralPath $OutputPath -Value $content -NoNewline

Write-Host "Done. Wrote final recolored file to $OutputPath"