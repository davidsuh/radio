import RPi.GPIO as GPIO

class audio:

	def audio_setup(self):
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
		
		# start on system audio
		GPIO.output(20, 0)
		GPIO.output(21, 1)

	def bt_volume_up(self):
		GPIO.output(5, 0)
		GPIO.output(5, 1)

	def bt_volume_down(self):
		GPIO.output(26, 0)
		GPIO.output(26, 1)

	def bt_prev_track(self):
		GPIO.output(6, 0)
		GPIO.output(6, 1)

	def bt_next_track(self):
		GPIO.output(19, 0)
		GPIO.output(19, 1)

	def bt_play_pause(self):
		GPIO.output(13, 0)
		GPIO.output(13, 1)

	def system_en(self):
		GPIO.output(20, 0)
		GPIO.output(21, 1)

	def radio_en(self):
		GPIO.output(20, 0)
		GPIO.output(21, 0)

	def bt_en(self):
		GPIO.output(20, 1)
		GPIO.output(21, 0)


