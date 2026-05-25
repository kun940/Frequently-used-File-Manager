Set-ShellAdmin -Verb RunAs
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\高频文件夹管理器.lnk")
$Shortcut.TargetPath = "C:\Users\29363\AppData\Local\Programs\Python\Python314\python.exe"
$Shortcut.Arguments = "`"d:\MyProjectCode\Vibe Coding Program\高频文件夹管理器\main.py`""
$Shortcut.WorkingDirectory = "d:\MyProjectCode\Vibe Coding Program\高频文件夹管理器"
$Shortcut.Description = "高频文件夹管理器"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,4"
$Shortcut.Save()
Write-Host "快捷方式已创建到桌面"
