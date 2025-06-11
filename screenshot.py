import mss, os
from PIL import Image

def screenshot(item_name, update_type, camname):
    with mss.mss() as sct:
        monitors = sct.monitors  # list of monitors

        # these are my monitors :)
        # monitors[0] virtual full screen
        # monitors[1] main monitor
        # monitors[2] right monitor
        # monitors[3] top monitor
        # monitors[4] left monitor

        monitor_number = 2  # change this to the monitor you want (e.g., 2 for second monitor)
        monitor = monitors[monitor_number]

        # change these to define the region you want to capture
        # this currently captures camera slot 5 assuming fullscreen and the monitor is 1920x1080
        region = {
            "top": monitor["top"] + 720,
            "left": monitor["left"] + 640,
            "width": 640,
            "height": 360
        }

        if update_type == 'preset':
            folder_path = f'images/tmp/{camname}'
        elif update_type == 'multicam':
            folder_path = 'images/tmp'
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        output_path = os.path.join(folder_path, f'{item_name}.png')
        
        screenshot = sct.grab(region)

        if update_type == 'preset':
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            resized_img = img.resize((320, 180), Image.LANCZOS)
            resized_img.save(output_path)
        elif update_type == 'multicam':
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=output_path)
        return output_path