import subprocess
from PIL import Image, ImageChops
from pytesseract import pytesseract
import re
import time
import random
import cv2
import numpy as np
import mss
from datetime import datetime

method = cv2.TM_CCOEFF_NORMED

last_sci = None
last_arch = None
last_pat = None

time_sci = time.time() - 120
time_arch = time.time() - 120
time_pat = time.time() - 120


def imagesearch(image, precision=0.8, custom_image=None):
    with mss.mss() as sct:
        # im = sct.grab(sct.monitors[0])
        # im.save('testarea.png') useful for debugging purposes, this will save the captured region as "testarea.png"
        # pipe = subprocess.Popen("adb -s 127.0.0.1:5555 exec-out screencap -p > screen.png",shell=True).wait()
        # image_bytes = pipe.stdout.read().replace(b'\r\n', b'\n')
        # img_gray = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        if custom_image:
            img_rgb = np.array(custom_image)
        else:
            img_rgb = np.array(take_screenshot())
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        # img_gray = None
        # while img_gray is None:

        # img_gray = cv2.imread('screen.png', 0)
        template = cv2.imread(image, 0)
        if template is None:
            raise FileNotFoundError('Image file not found: {}'.format(image))
        template.shape[::-1]

        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val < precision:
            return -1, -1
        return max_loc


def click(x, y):
    """
    Click at the given (x, y) coordinate
    """
    subprocess.run(['adb', '-s', '127.0.0.1:5555', 'shell', 'input', 'tap', str(x), str(y)])


def draganddrop(x1, y1, x2, y2):
    """
    Click at the given (x, y) coordinate
    """
    subprocess.run(['adb', '-s', '127.0.0.1:5555', 'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2)])


def take_screenshot():
    """
    Take a screenshot of the emulator
    """
    screenshot_bytes = subprocess.run(['adb', '-s', '127.0.0.1:5555', 'exec-out', 'screencap'], check=True,
                                      capture_output=True).stdout
    screenshot = Image.frombuffer('RGBA', (900, 1600), screenshot_bytes[12:], 'raw', 'RGBX', 0, 1)
    screenshot = screenshot.convert('RGB').resize((900, 1600), Image.BILINEAR)
    return screenshot


def coordinates_shared():
    coordinates_found = []
    template = cv2.imread('share_coordinates.png')
    img_rgb = cv2.cvtColor(np.array(take_screenshot()), cv2.COLOR_BGR2RGB)
    h, w = template.shape[:2]

    res = cv2.matchTemplate(img_rgb, template, cv2.TM_CCOEFF_NORMED)

    threshold = 0.95
    loc = np.where(res >= threshold)

    tree_count = 0
    mask = np.zeros(img_rgb.shape[:2], np.uint8)
    for pt in zip(*loc[::-1]):
        if mask[pt[1] + int(round(h / 2)), pt[0] + int(round(w / 2))] != 255:
            mask[pt[1]:pt[1] + h, pt[0]:pt[0] + w] = 255
            tree_count += 1
            # cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 1)
            coordinates_found.append(pt)

    max_y = 0
    coordinates_to_return = None
    for c in coordinates_found:
        x, y = c
        if y > max_y:
            max_y = y
            coordinates_to_return = c

    return coordinates_to_return


try:
    subprocess.run(['adb', 'start-server'])
    subprocess.run(['adb', 'connect', '127.0.0.1:5555'])
    window_size = subprocess.check_output(['adb', '-s', '127.0.0.1:5555', 'shell', 'wm', 'size'])
except subprocess.CalledProcessError as e:
    raise RuntimeError(f"command '{e.cmd}' return with error (code {e.returncode}): {e.output}")
window_size = window_size.decode('ascii').replace('Physical size: ', '')
width, height = [int(i) for i in window_size.split('x')]
# Defining paths to tesseract.exe
# and the image we would be using
path_to_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# image_path = r"csv\sample_text.png"

# Opening the image & storing it in an image object
# img = Image.open(image_path)

# Providing the tesseract executable
# location to pytesseract library
pytesseract.tesseract_cmd = path_to_tesseract

# Passing the image object to image_to_string() function
# This function will extract the text from the image
# text = pytesseract.image_to_string(take_screenshot())

# print(imagesearch('architect.png'))

screenshot_old = take_screenshot()

j = 0

while True:
    screenshot_new = take_screenshot()
    if True:  # ImageChops.difference(screenshot_old.crop((200, 270, 900, 1490)), screenshot_new.crop((200, 270, 900, 1490))).getbbox():
        # print("image diff found")
        screenshot_old = screenshot_new
        coordinates_found = coordinates_shared()
        if coordinates_found:
            x, y = coordinates_found
            # search above the image
            if x + 500 < 900 and y - 250 > 0:
                area_of_interest = screenshot_new.crop((x, y - 250, x + 500, y))
                area_of_interest = cv2.cvtColor(np.array(area_of_interest), cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(area_of_interest)
                text = [i.lower() for i in text.split('\n') if i]
                tn_found = [k for k in text if '-n' in k]
                if tn_found:
                    requestor = re.sub('\W+', '', tn_found[0].split('-n')[-1])
                    sci_found = [k for k in text if 'sci' in k]
                    arch_found = [k for k in text if 'arch' in k]
                    pat_found = [k for k in text if 'pat' in k]
                    if sci_found and time_sci - time.time() < - 60 and requestor and requestor != last_sci:
                        print(datetime.now().strftime('%H:%M:%S') + "Found Scientist request")
                        last_sci = requestor
                        # in case someone wrote a message before we clicked on the shared coordinates
                        x, y = coordinates_shared()
                        if x != -1:
                            click(x + random.randint(0, 500), y + random.randint(0, 80))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            x = -1
                            for k in range(5):
                                if x == -1:
                                    click(450, 800)
                                    time.sleep(random.randint(2000, 3000) / 1000)
                                    # sometimes the title button is visible in the drop down list of options when you click on a base
                                    x, y = imagesearch('title_bio.png')
                                    if x == -1:
                                        x, y = imagesearch('title.png')
                                else:
                                    break
                            if x != -1:
                                click(x + random.randint(0, 200), y + random.randint(0, 40))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            else:
                                click(random.randint(400, 500), random.randint(1590, 1595))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            draganddrop(450, 1200, 450, 900)
                            time.sleep(random.randint(3000, 4000) / 1000)
                            # look for the word patriot
                            x, y = imagesearch('scientist.png')
                            if x != -1:
                                print(datetime.now().strftime('%H:%M:%S') + "Granting Scientist request")
                                last_sci = requestor
                                # Appoint
                                click(x + random.randint(0, 100), y + random.randint(130, 170))
                                # yes
                                time.sleep(random.randint(1000, 2000) / 1000)
                                click(random.randint(180, 360),
                                      random.randint(955, 1000))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            # exit title screen
                            x, y = imagesearch('x.png')
                            while x != -1:
                                click(x + random.randint(0, 10), y + random.randint(0, 10))
                                time.sleep(random.randint(1000, 2000) / 1000)
                                x, y = imagesearch('x.png')
                            click(random.randint(300, 600), random.randint(1440, 1470))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            time_sci = time.time()

                    elif pat_found and time_pat - time.time() < - 60 and requestor and requestor != last_pat:
                        print(datetime.now().strftime('%H:%M:%S') + "Found Patriot request")
                        last_pat = requestor
                        x, y = coordinates_shared()
                        if x != -1:
                            click(x + random.randint(0, 500), y + random.randint(0, 80))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            x = -1
                            for k in range(5):
                                if x == -1:
                                    click(450, 800)
                                    time.sleep(random.randint(2000, 3000) / 1000)
                                    # sometimes the title button is visible in the drop down list of options when you click on a base
                                    x, y = imagesearch('title_bio.png')
                                    if x == -1:
                                        x, y = imagesearch('title.png')
                                else:
                                    break
                            if x != -1:
                                click(x + random.randint(0, 200), y + random.randint(0, 40))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            else:
                                click(random.randint(400, 500), random.randint(1590, 1595))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            draganddrop(450, 1200, 450, 900)
                            time.sleep(random.randint(3000, 4000) / 1000)
                            # look for the word patriot
                            x, y = imagesearch('patriot.png')
                            if x != -1:
                                print(datetime.now().strftime('%H:%M:%S') + "Granting Patriot request")
                                last_pat = requestor
                                # Appoint
                                click(x + random.randint(0, 100), y + random.randint(130, 170))
                                # yes
                                time.sleep(random.randint(1000, 2000) / 1000)
                                click(random.randint(180, 360),
                                      random.randint(955, 1000))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            # exit title screen
                            x, y = imagesearch('x.png')
                            while x != -1:
                                click(x + random.randint(0, 10), y + random.randint(0, 10))
                                time.sleep(random.randint(1000, 2000) / 1000)
                                x, y = imagesearch('x.png')
                            click(random.randint(300, 600), random.randint(1440, 1470))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            time_pat = time.time()
                    if arch_found and time_arch - time.time() < - 60 and requestor and requestor != last_arch:
                        print(datetime.now().strftime('%H:%M:%S') + "Found Architect request")
                        x, y = coordinates_shared()
                        if x != -1:
                            click(x + random.randint(0, 500), y + random.randint(0, 80))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            x = -1
                            for k in range(5):
                                if x == -1:
                                    click(450, 800)
                                    time.sleep(random.randint(2000, 3000) / 1000)
                                    # sometimes the title button is visible in the drop down list of options when you click on a base
                                    x, y = imagesearch('title_bio.png')
                                    if x == -1:
                                        x, y = imagesearch('title.png')
                                else:
                                    break
                            if x != -1:
                                click(x + random.randint(0, 200), y + random.randint(0, 40))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            else:
                                click(random.randint(400, 500), random.randint(1590, 1595))
                                time.sleep(random.randint(1000, 2000) / 1000)
                            draganddrop(450, 1200, 450, 850)
                            time.sleep(random.randint(3000, 4000) / 1000)
                            # look for the word patriot
                            x, y = imagesearch('architect.png')
                            if x != -1:
                                print(datetime.now().strftime('%H:%M:%S') + "Granting Architect request")
                                last_arch = requestor
                                # Appoint
                                click(x + random.randint(0, 100), y + random.randint(130, 170))
                                # yes
                                time.sleep(random.randint(1000, 2000) / 1000)
                                click(random.randint(180, 360),
                                      random.randint(955, 1000))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            # exit title screen
                            x, y = imagesearch('x.png')
                            while x != -1:
                                click(x + random.randint(0, 10), y + random.randint(0, 10))
                                time.sleep(random.randint(1000, 2000) / 1000)
                                x, y = imagesearch('x.png')
                            click(random.randint(300, 600), random.randint(1440, 1470))
                            time.sleep(random.randint(1000, 2000) / 1000)
                            time_arch = time.time()

    time.sleep(15)
    j = j + 1
    # check if we're on main screen for some reason
    if j % 5 == 0:
        x, y = imagesearch('profile_pic.png')
        if x != -1:
            click(random.randint(300, 600), random.randint(1440, 1470))
            time.sleep(random.randint(1000, 2000) / 1000)
        # check if we're on title screen for some reason
        x, y = imagesearch('x.png')
        if x != -1:
            click(x + random.randint(0, 10), y + random.randint(0, 10))
            time.sleep(random.randint(1000, 2000) / 1000)
            click(random.randint(300, 600), random.randint(1440, 1470))
            time.sleep(random.randint(1000, 2000) / 1000)
        # check if we're on airplane page for some reason
        x, y = imagesearch('airplane.png')
        if x != -1:
            x, y = imagesearch('two_arrows_back.png')
            if x != -1:
                click(x + random.randint(0, 10), y + random.randint(0, 10))
                time.sleep(random.randint(1000, 2000) / 1000)
                click(random.randint(300, 600), random.randint(1440, 1470))
                time.sleep(random.randint(1000, 2000) / 1000)

        # check if we should shut down
        text = pytesseract.image_to_string(screenshot_new)
        text = [i.lower() for i in text.split('\n') if i]
        turn_off = [k for k in text if 'minister off' in k]
        turn_sleep = [k for k in text if 'minister sleep' in k]
        if turn_off:
            exit()
        elif turn_sleep:
            time.sleep(1800). IS

        #check if we're on some weird page
        x, y = imagesearch('two_arrows_back.png')
        if x != -1:
            click(x + random.randint(0, 10), y + random.randint(0, 10))
            time.sleep(random.randint(1000, 2000) / 1000)
            click(random.randint(300, 600), random.randint(1440, 1470))
            time.sleep(random.randint(1000, 2000) / 1000)
