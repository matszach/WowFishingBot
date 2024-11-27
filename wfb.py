import pyautogui
from win32 import win32gui
import time
from PIL import ImageGrab
import json
from random import random


# =========================================== config read =================================================
with open('./config.json') as f:
	config = json.loads(f.read())


# =========================================== runtime variables ===========================================
vars = {
	"wasAreaOutlined": False,
	"isRodCast": False,
	"nofCasts": 0,
	"nofLures": 0,
	"bobberLocated": False,
	"bobberX": -1,
	"bobberY": -1,
	"lureLastApplied": time.time() if config['misc']['ignoreFirstLureApply'] else -1,
	"currChecks": 0,
	"avgR": 0,
	"avgG": 0,
	"avgB": 0,
	"timesBobberLocatedSuccess": 0,
	"timesBobberLocatedFailure": 0,
}


# =========================================== functions ===================================================
def wait(duration):
	# print(f'waiting for {duration}')
	time.sleep(duration)

def is_wow_open(window):
	return win32gui.GetWindowText(window) == config['meta']['wowWindowName']

def get_window_rect(window):
	return win32gui.GetWindowRect(window)

def get_checked_area(window_rect):
	return (
		config['fishingAreaMargin']['left'],
		config['fishingAreaMargin']['top'],
		window_rect[2] - config['fishingAreaMargin']['right'],
		window_rect[3] - config['fishingAreaMargin']['bottom']
	)

def get_image(window_rect):
	return ImageGrab.grab(window_rect)

def find_bobber(window):
	window_rect = get_window_rect(window)
	area_rect = get_checked_area(window_rect)
	window_image = get_image(area_rect)
	w, h = window_image.size

	if config['debug']['outputCheckedArea']:
		window_image.save('checkedArea.png')

	for x in range(0, w, 2):
		for y in range(0, h, 2):
			r, g, b = window_image.getpixel((x, y))
			if match_rgb(r, g, b):
				return x, y, True
	return 0, 0, False

def match_rgb(r, g, b):
	min_r = config['bobberRGB']['red']['min']
	max_r = config['bobberRGB']['red']['max']
	min_g = config['bobberRGB']['green']['min']
	max_g = config['bobberRGB']['green']['max']
	min_b = config['bobberRGB']['blue']['min']
	max_b = config['bobberRGB']['blue']['max']
	return (min_r <= r <= max_r and min_g <= g <= max_g and min_b <= b <= max_b)

def rng(base, variation):
	return base + base * (2 * variation * random() - variation)

def outiline_fishing_area(window):
	print('Outlining the fishing area ...')
	window_rect = get_window_rect(window)
	pyautogui.moveTo(config['fishingAreaMargin']['left'], config['fishingAreaMargin']['top'], 0.3)
	pyautogui.moveTo(window_rect[2] - config['fishingAreaMargin']['right'], config['fishingAreaMargin']['top'], 0.3)
	pyautogui.moveTo(window_rect[2] - config['fishingAreaMargin']['right'], window_rect[3] - config['fishingAreaMargin']['bottom'], 0.3)
	pyautogui.moveTo(config['fishingAreaMargin']['left'], window_rect[3] - config['fishingAreaMargin']['bottom'], 0.3)
	pyautogui.moveTo(config['fishingAreaMargin']['left'], config['fishingAreaMargin']['top'], 0.3)
	pyautogui.moveTo(
		config['fishingAreaMargin']['left'] + (window_rect[2] - config['fishingAreaMargin']['left'] - config['fishingAreaMargin']['right']) / 2, 
		config['fishingAreaMargin']['top'] + (window_rect[3] - config['fishingAreaMargin']['top'] - config['fishingAreaMargin']['bottom']) / 2,
		0.3
	)
	vars['wasAreaOutlined'] = True
	wait(3)

def get_avg_rgb_around_bobber(window):
	x = vars['bobberX']
	y = vars['bobberY']
	window_rect = get_window_rect(window)
	bobber_area = (
		config['fishingAreaMargin']['left'] + x - 75, 
		config['fishingAreaMargin']['top'] + y - 75, 
		config['fishingAreaMargin']['left'] + x + 75, 
		config['fishingAreaMargin']['top'] + y + 75
	)
	bobber_image = get_image(bobber_area)
	n = 0
	tot_r = 0
	tot_g = 0
	tot_b = 0
	w, h = bobber_image.size
	for x in range(0, w, 2):
		for y in range(0, h, 2):
			r, g, b = bobber_image.getpixel((x, y))
			tot_r += r
			tot_g += g
			tot_b += b
			n += 1
	return tot_r/n, tot_g/n, tot_b/n

def outline_bobber_area(x, y):
	if not config['debug']['outlineBobberBox']:
		return
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x - 75, config['fishingAreaMargin']['top'] + y - 75, 0.3)
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x + 75, config['fishingAreaMargin']['top'] + y - 75, 0.2)
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x + 75, config['fishingAreaMargin']['top'] + y + 75, 0.2)
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x - 75, config['fishingAreaMargin']['top'] + y + 75, 0.2)
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x - 75, config['fishingAreaMargin']['top'] + y - 75, 0.2)

def alter_bite_check_vars(r, g, b):
	vars['avgR'] = (vars['avgR'] * vars['currChecks'] + r) / (vars['currChecks'] + 1)
	vars['avgG'] = (vars['avgG'] * vars['currChecks'] + g) / (vars['currChecks'] + 1)
	vars['avgB'] = (vars['avgB'] * vars['currChecks'] + b) / (vars['currChecks'] + 1)
	vars['currChecks'] += 1

def check_for_bite(r, g, b):
	n = vars['currChecks']
	if n > config['performance']['maxTicksPerLure']:
		return True
	dR = abs(r - vars['avgR'])
	dG = abs(g - vars['avgG'])
	dB = abs(b - vars['avgB'])
	match = (
		n > config['collection']['minTicks'] and 
		(
			dR > config['collection']['threshold']['red'] or 
			dG > config['collection']['threshold']['green'] or 
			dB > config['collection']['threshold']['blue']
		)
	)
	if config['debug']['printRGBDeviations']:
		print(f'n: {n}, dR: {round(dR, 2)}, dG: {round(dG, 2)}, dB: {round(dB, 2)} {" (matches!)" if match else ""}')
	return match

def reset_bite_check_vars():
	vars['avgR'] = 0
	vars['avgG'] = 0
	vars['avgB'] = 0
	vars['currChecks'] = 0

def collect():
	print('A bite detected!')
	wait(rng(1, 0.2))	
	if config['debug']['dontCollect']:
		return
	pyautogui.mouseDown(button='right')
	pyautogui.mouseUp(button='right')
	vars['bobberLocated'] = False
	vars['isRodCast'] = False
	reset_bite_check_vars()	
	wait(rng(2, 0.2))	

def should_apply_lure(t):
	use_macro = config['misc']['useLureMacro']
	time_to_apply = t > (vars['lureLastApplied'] + config['misc']['lureMacroInterval'])
	return use_macro and time_to_apply

def apply_lure(t):
	vars['nofLures'] += 1
	vars['lureLastApplied'] = t
	print(f'Applying the lure for the {vars["nofLures"]} time')
	pyautogui.press(config['keys']['lureMacro'])
	wait(rng(6, 0.05))

def cast_rod():
	vars['nofCasts'] += 1
	print(f'========== Casting rod for the {vars["nofCasts"]} time ==========')
	pyautogui.press(config['keys']['castRod'])
	vars['isRodCast'] = True
	wait(rng(3, 0.2))

def focus_on_bobber(x, y):
	vars['timesBobberLocatedSuccess'] += 1
	print(f'Bobber found at position x: {x}, y: {y}')
	outline_bobber_area(x, y)
	pyautogui.moveTo(config['fishingAreaMargin']['left'] + x, config['fishingAreaMargin']['top'] + y, rng(0.4, 0.3))
	vars['bobberLocated'] = True
	vars['bobberX'] = x
	vars['bobberY'] = y
	wait(rng(1, 0.2))

def ready_recast():
	vars['timesBobberLocatedFailure'] += 1
	print('Could not locate the bobber! Recasting soon ...')
	vars['isRodCast'] = False

def wait_for_wow():
	print('Waiting for World of Warcraft ...')
	vars['wasAreaOutlined'] = False
	wait(3)

def print_location_stats():
	s = vars['timesBobberLocatedSuccess']
	f = vars['timesBobberLocatedFailure']
	perc = 0 if (s + f) == 0 else round(100 * s / (s + f), 2)
	print(f'{perc}% ({s}/{s + f}) location accuracy.')

# =========================================== Main Loop ===================================================
while True:

	# get most foreground window
	window = win32gui.GetForegroundWindow()

	# is wow open ?
	if not is_wow_open(window):
		wait_for_wow()

	# area outline displaying
	elif not vars['wasAreaOutlined']:
		outiline_fishing_area(window)

	# attempting to fish
	else:

		# is a rod already cast ?
		if not vars['isRodCast']:
			t = time.time()
			if should_apply_lure(t):
				apply_lure(t)
			else:
				cast_rod()
			print_location_stats()
				
		# does the bobber need to be located ?
		elif not vars['bobberLocated']:
			x, y, found = find_bobber(window)
			if found:
				focus_on_bobber(x, y)
			else:
				ready_recast()

		# checking if there's a bite
		else: 
			r, g, b = get_avg_rgb_around_bobber(window)
			alter_bite_check_vars(r, g, b)
			if check_for_bite(r, g, b):
				collect()
