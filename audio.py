import RPi.GPIO as GPIO

class audio:

	def audio_setup():
		GPIO.setmode(GPIO.BCM)

		# bluetooth control GPIO setup
		GPIO.setup(5, GPIO.OUT)		# volume up
		GPIO.setup(6, GPIO.OUT)		# prev track
		GPIO.setup(13, GPIO.OUT)	# play/pause
		GPIO.setup(19, GPIO.OUT)	# next track
		GPIO.setup(26, GPIO.OUT)	# volume down

		# MUX control GPIO setup
		GPIO.setup(20, GPIO.OUT)
		GPIO.setup(21, GPIO.OUT)

	def bt_volume_up():
		GPIO.output(5, 0)

	def bt_volume_down();
		GPIO.output(26, 0)

	def bt_prev_track():
		GPIO.output(6, 0)

	def bt_next_track():
		GPIO.output(19, 0)

	def bt_play_pause():
		GPIO.output(13, 0)

	def system_en():
		GPIO.output(20, 0)
		GPIO.output(21, 1)

	def radio_en():
		GPIO.output(20, 0)
		GPIO.output(21, 0)

	def bt_en():
		GPIO.output(20, 1)
		GPIO.output(21, 0)


