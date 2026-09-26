$dirs = @(
    "backend\app\api\endpoints",
    "backend\app\core",
    "backend\app\models",
    "backend\app\schemas",
    "backend\app\services",
    "backend\app\ml",
    "backend\app\photogrammetry",
    "backend\app\processing",
    "backend\tests",
    "data\raw",
    "data\processed",
    "data\surveys",
    "data\demo",
    "models\material",
    "models\deterioration",
    "outputs\3d",
    "outputs\reports",
    "outputs\analysis",
    "docs\architecture",
    "docs\methodology",
    "docs\research",
    "scripts"
)
foreach ($d in $dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Path $d -Force | Out-Null
    }
}

$keepDirs = @("data\raw", "data\processed", "data\surveys", "data\demo", "outputs\3d", "outputs\reports", "outputs\analysis")
foreach ($kd in $keepDirs) {
    $kf = Join-Path $kd ".gitkeep"
    if (-not (Test-Path $kf)) {
        New-Item -ItemType File -Path $kf -Force | Out-Null
    }
}
Write-Output "Directory layout created successfully."
