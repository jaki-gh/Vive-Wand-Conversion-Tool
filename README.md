<img width="100" height="100" alt="Untitled design" src="https://github.com/user-attachments/assets/99d52246-7d50-41bc-a423-b4ff5c9f964f" />



# About
**This GUI tool written in Python converts HTC Vive Wand controllers into Vive Trackers for full body tracking! Previously, users had to use command line tools deep within SteamVR's files and edit json files by hand, but this app makes it easy as clicking a few buttons!**

## Features

- HMD checking to prevent accidental headset bricking
- Automatic controller detection
- Easily revert back to controller firmware
- Organized json file management
- Automatic `lighthouse_console.exe` detection
- Clean and easy to use GUI.

## How to use

1. Ensure SteamVR is installed on your device.

2. Unplug all SteamVR devices from your computer.

3. Plug the controller you want to convert into your computer with a USB cable (make sure this is the only SteamVR device that is plugged in!)

4. Download and run either the Python script or the Windows executable. 

5. The app should automatically detect your `lighthouse_console.exe` that is usually located in `C:\Program Files (x86)\Steam\steamapps\common\SteamVR\tools\lighthouse\bin\win64`. If the .exe is not found, then you can manually select the file using the "Browse..." button.

6. Press the "Detect serial" button to automatically detect your Vive Wand.

7. Press "Convert to Tracker" to run the install script.

8. Once the script is complete, you can unplug the Wand from USB and reconnect all your SteamVR devices.

9. Start SteamVR and your controller should now appear as a tracker!

## Convert back to controller

If you want to return your controller to its original controller self, all you need to do is follow the instructions above but press "Restore Controller" instead of "Convert to Tracker".

All the generated json config files are stored in a folder called `configs` in the same directory as `lighthouse_console.exe`.



## Donation page for poorness reasons
 [![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Q5Q6TOTSN)
