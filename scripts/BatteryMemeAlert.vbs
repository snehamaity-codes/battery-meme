Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\HACKATHON\battery"
WshShell.Run """C:\Users\WORK_SNEHA\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""D:\HACKATHON\battery\src\battery_meme_alert.py""", 0, False
