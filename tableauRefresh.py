import pyautogui
import time
import subprocess
import os
import pygetwindow as gw

tableau_path = r"C:\Program Files\Tableau\Tableau 2024.3\bin\tableau.exe"
workbook_path = r"C:\Users\Olivia Croteau\Documents\My Tableau Repository\Workbooks\AegisAnalytics.twb"
# Check if the paths exist
if os.path.exists(tableau_path) and os.path.exists(workbook_path):
    print("Both paths exist, running Tableau...")
    process = subprocess.Popen([tableau_path, workbook_path])
    time.sleep(10)  # Wait for Tableau to open

    window = gw.getWindowsWithTitle("Tableau")[0]
    window.activate()

    
    # Refresh Extract
    print("opening data menups")
    pyautogui.hotkey("alt", "d")  # Open Data menups
    time.sleep(1)
    pyautogui.press("down")
    pyautogui.press("down")
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(10)
    print("data extract refreshed")

    # Google auth
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")

    time.sleep(5)
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")

    time.sleep(5)
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")
    
    # Back to tableau
    window.activate()
    time.sleep(8)
    # Save to Tableau Public
    pyautogui.press("enter")
    time.sleep(2)  # Give Tableau time to fully activate
    window.activate()
    pyautogui.hotkey("alt", "s")  # Open Server menu
    time.sleep(1)
    pyautogui.press("down")  # Open Tableau Public
    pyautogui.press("down")     
    pyautogui.press("down")
    pyautogui.press("down")
    pyautogui.press("down")
    pyautogui.press("down")
    pyautogui.press("down")
    pyautogui.press("enter")
    pyautogui.press("down")
    pyautogui.press("enter")
    time.sleep(10)

    # Google auth
    
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")

    time.sleep(5)
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")

    time.sleep(5)
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("tab")
    pyautogui.press("enter")
    

    print("Tableau Public dashboard updated successfully!")

else:
    print("One or both paths do not exist.")