# Menyalakan NiFi di Windows (folder NiFi\ di sini). Pakai: powershell -File hidupkan_nifi.ps1  (stop: -Stop)
# NiFi diakses lewat junction C:\nifi (path tanpa spasi dan &). HDFS tetap di WSL (localhost:9000).
param([switch]$Stop)
$ErrorActionPreference = 'Stop'
$src = Join-Path $PSScriptRoot 'NiFi'
if (-not (Test-Path 'C:\nifi')) { New-Item -ItemType Junction -Path 'C:\nifi' -Target $src | Out-Null }
if ($Stop) {
  Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object CommandLine -match 'nifi' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
  'NiFi dihentikan.'; exit 0
}
$jdk = (Get-ChildItem 'C:\Program Files\Java' -Directory | Where-Object Name -match '^jdk-(2[1-9]|[3-9]\d)' | Sort-Object Name -Descending | Select-Object -First 1).FullName
if (-not $jdk) { throw 'Butuh JDK 21 atau lebih baru (NiFi 2.x).' }
$env:JAVA_HOME = $jdk
$env:HADOOP_USER_NAME = 'lenovo'   # PutHDFS menulis sebagai pemilik /data/raw di HDFS
if (Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object CommandLine -match 'nifi') { 'NiFi sudah berjalan.' }
else { Start-Process -WindowStyle Minimized -FilePath cmd.exe -ArgumentList '/c','C:\nifi\nifi-2.12.0\bin\nifi.cmd run' -WorkingDirectory 'C:\nifi\nifi-2.12.0' }
Write-Host 'Menunggu NiFi (1-3 menit)...'
for ($i = 0; $i -lt 60; $i++) {
  try { if ((curl.exe -sk -o NUL -m3 -w '%{http_code}' https://localhost:8443/nifi/) -eq '200') { Write-Host 'NiFi SIAP: https://localhost:8443/nifi (user root)'; exit 0 } } catch {}
  Start-Sleep 5
}
Write-Host 'NiFi belum siap; cek C:\nifi\nifi-2.12.0\logs\nifi-app.log'
