$ErrorActionPreference = "Stop"

# === 配置：可按需修改 ===
$SdkRoot = "C:\Android\Sdk"
$CmdlineZipUrl = "https://dl.google.com/android/repository/commandlinetools-win-9477386_latest.zip"
$CmdlineZip = "$env:TEMP\cmdline-tools.zip"
$BuildToolsVersion = "34.0.0"
$PlatformApi = "android-34"

Write-Host "SDK root: $SdkRoot"

# 1) 准备目录
New-Item -ItemType Directory -Force -Path "$SdkRoot\cmdline-tools" | Out-Null

# 2) 下载 commandline tools
Write-Host "Downloading commandline tools ..."
Invoke-WebRequest -Uri $CmdlineZipUrl -OutFile $CmdlineZip

# 3) 解压并放到 cmdline-tools\latest
Write-Host "Extracting ..."
Expand-Archive $CmdlineZip -DestinationPath "$SdkRoot\cmdline-tools\temp" -Force
if (-Not (Test-Path "$SdkRoot\cmdline-tools\temp\cmdline-tools")) {
    throw "Unexpected zip layout, 'cmdline-tools' folder not found."
}
if (Test-Path "$SdkRoot\cmdline-tools\latest") { Remove-Item "$SdkRoot\cmdline-tools\latest" -Recurse -Force }
Move-Item "$SdkRoot\cmdline-tools\temp\cmdline-tools" "$SdkRoot\cmdline-tools\latest"
Remove-Item "$SdkRoot\cmdline-tools\temp" -Recurse -Force

# 4) 更新临时 PATH 以使用 sdkmanager
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:PATH = "$SdkRoot\cmdline-tools\latest\bin;$SdkRoot\platform-tools;$env:PATH"

# 5) 安装基础组件
Write-Host "Accepting licenses ..."
"y`n" * 50 | sdkmanager --sdk_root=$SdkRoot --licenses | Out-Host

Write-Host "Installing platform-tools, build-tools, platforms ..."
sdkmanager --sdk_root=$SdkRoot @(
    "platform-tools",
    "build-tools;$BuildToolsVersion",
    "platforms;$PlatformApi",
    "cmdline-tools;latest"
) | Out-Host

Write-Host "`nDone. Remember to set local.properties in your Android project, e.g.:"
Write-Host "sdk.dir=$SdkRoot"
Write-Host "`nIf using WSL, the path is: /mnt/c/Android/Sdk"


