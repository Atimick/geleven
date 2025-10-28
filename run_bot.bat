@echo off
cd "C:/Users/nguye/Downloads/DC_Bot_Geleven/"
timeout /t 5 /nobreak > nul
code . --wait --command "workbench.action.terminal.new" --command "workbench.action.terminal.sendSequence" --arg "text=python Discord_Bot_Geleven.py\n"