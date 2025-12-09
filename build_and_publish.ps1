$ErrorActionPreference = "Stop"

# 路径配置：按需修改
$javaHome   = "C:\Program Files\Eclipse Adoptium\jdk-17.0.17.10-hotspot"
$sdkRoot    = "C:\Android\Sdk"
# 自动定位当前仓库根目录，避免中文路径乱码
$projRoot   = (Resolve-Path $PSScriptRoot).Path
$androidDir = Join-Path $projRoot "ExamMasterAndroid"

# 如果上一行仍找不到，尝试上一级目录
if (-not (Test-Path $androidDir)) {
    $projRoot = (Resolve-Path (Split-Path -Parent $projRoot)).Path
    $androidDir = Join-Path $projRoot "Lovepython\ExamMasterAndroid"
}

if (-not (Test-Path $androidDir)) {
    throw "Android 项目目录不存在: $androidDir"
}

Write-Host "设置 JAVA_HOME / PATH ..."
$env:JAVA_HOME = $javaHome
$env:PATH      = "$javaHome\bin;$env:PATH"

Write-Host "写入 local.properties ..."
Set-Location $androidDir
@"
sdk.dir=$sdkRoot
"@ | Out-File -Encoding UTF8 local.properties

Write-Host "编译 APK (assembleDebug) ..."
if (Test-Path ".\gradlew.bat") {
    .\gradlew.bat assembleDebug
} else {
    # 如果没有 .bat，可在 Git Bash/WSL 用 ./gradlew
    ./gradlew assembleDebug
}

Write-Host "发布 APK 到 static/apk/latest.apk ..."
Set-Location $projRoot
python tools\publish_apk.py

Write-Host "完成。最新 APK 已复制到 static/apk/latest.apk"