Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)
strProjectRoot = objFSO.GetParentFolderName(strScriptDir)
strPythonW = objFSO.BuildPath(strProjectRoot, "venv\Scripts\pythonw.exe")
strRunScript = objFSO.BuildPath(strProjectRoot, "scripts\run_server.py")

objShell.CurrentDirectory = strProjectRoot
objShell.Run """" & strPythonW & """ """ & strRunScript & """", 0, False
