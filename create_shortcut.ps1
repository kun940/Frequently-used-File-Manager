$exePath = "d:\MyProjectCode\Vibe Coding Program\高频文件夹管理器\dist\高频文件夹管理器.exe"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\高频文件夹管理器.lnk")
$Shortcut.TargetPath = $exePath
$Shortcut.WorkingDirectory = Split-Path $exePath
$Shortcut.Description = "高频文件夹管理器"
$Shortcut.IconLocation = "$exePath,0"
$Shortcut.Save()
Write-Host "快捷方式已创建到桌面"
