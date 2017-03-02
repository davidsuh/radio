from time import sleep,time
from datetime import datetime
import threading		

ptydict_eu = {0 : "Unknown",1 : "News",2 : "Current Affairs",3 : "Information",4 : "Sports",5 : "Education",6 : "Drama",7 : "Culture",8 : "Science",9 : "Various" , \
	10 : "Pop",11 : "Rock",12 : "Easy Listening",13 : "Light Classical",14 : "Serious Classical",15 : "Other Music",16 : "Weather",17 : "Finance",18 : "Children", \
        19 : "Social Affairs",20 : "Religion",21 : "Phone in",22 : "Travel",23 : "Leisure",24 : "Jazz",25 : "Country",26 : "National",27 : "Oldies",28 : "Folk", \
        29 : "Documentary",30 : "Alarm Test",31 : "Alarm"}   

ptydict_na = {0 : "Unknown",1 : "News",2 : "Information",3 : "Sports",4 : "Talk",5 : "Rock",6 : "Classic Rock",7 : "Adult hits",8 : "Soft rock",9 : "Top 40" , \
	10 : "Country",11 : "Oldies",12 : "Soft",13 : "Nostalgia",14 : "Jazz",15 : "Classical",16 : "Rhythm and Blues",17 : "Soft rhythm and blues",18 : "Language", \
        19 : "Religious music",20 : "Religious talk",21 : "Personality",22 : "Public",23 : "College",24 : "Spanish talk",25 : "Spanish music",26 : "Hop Hop", \
        27 : "Unassigned",28 : "Unassigned", 29 : "Weatjer",30 : "Emergency Test",31 : "Eemergency"}


# Declare these here so they are accessible back in our main program 

class si4703:
    '''
    Each sub-class in this file represents a register within the si4703 capable of being read.
    Not all registers are capable of being written to
    Some bits are capable of being written to, but should always be set to zero. Such registers have commented placeholders.
    '''
    import smbus

    i2c = smbus.SMBus(1)
	
    PS=""
    RadioText=""
    pty=""
    
	# These are going to be used for a map of stations that provide tuning info and radiotext
	# They can be used in your application to decide if you want to scan these channels
	# or save the effort
    station_ps={}
    station_rt={}
 	
    ptydict=ptydict_na # Have to make an assumption. If we're in the US we may never get a country code over RDS

    def init(self):
        '''
        This is the initial setup for the Si4703. The encompasses setting up the GPIO pins on the Pi as the protocol for putting the Si4703 is 2-wire (read: "SMBus") mode
        The protocl is covered in the programming guide for the Si4703 dubbed "AN230"
        http://www.silabs.com/Support%20Documents/TechnicalDocs/AN230.pdf
        '''
        from time import sleep
        import RPi.GPIO as GPIO
		# I kept getting messages about the channel already being in use.. even though it is for this radio.
        GPIO.setwarnings(False)
		
        GPIO.setmode(GPIO.BCM)  ## We will use board numbering instead of pin numbering. 
        GPIO.setup(23 ,GPIO.OUT) ## RST
        GPIO.setup(0 ,GPIO.OUT)  ## SDA
        GPIO.output(0 ,GPIO.LOW) ## This block of code puts the Si4703 into 2-wire mode per instructions on page 7  of AN230
        sleep(.1)                ## Actually, I'm not sure how this block of code works. According to the aforementioned page 7, it shouldn't
        GPIO.output(23 ,GPIO.LOW) ## But I ripped this code off somewhere else, so I'm not gonna bash it. Great work to the OP
        sleep(.1)
        GPIO.output(23 ,GPIO.HIGH)
        sleep(0.5)
        
        si4703.update_registry(self)
        si4703.TEST_1.POWER_SEQUENCE = True
        si4703.write_registry(self)
        si4703.TEST_1.POWER_SEQUENCE = False
        sleep(.1)
        
        si4703.POWER_CONFIG.DMUTE = 1
        si4703.POWER_CONFIG.ENABLE = 1
#        si4703.write_registry(self)
#        sleep(.1)

        si4703.SYS_CONFIG_2.VOLUME = 7
        si4703.CHANNEL.CHAN = 85
        si4703.CHANNEL.TUNE = 1
        
        si4703.POWER_CONFIG.RDSM = 0    # This is the RDS Mode. It is set to either Standard(0) or Verbose(1). 
        				# The major difference is that verbose will read the groups regardless of errors.
                                        # I choose to stick with Standard mode so what I see when I parse is data that makes sense.
                                        
        si4703.SYS_CONFIG_1.RDS = 1            # Enable RDS
        si4703.SYS_CONFIG_1.RDSIEN = 1         # Enables interrupt on GPIO2
        si4703.SYS_CONFIG_1.GPIO2 = 1         # Tells GPIO2 that it is going to be the RDS Interrupt.
                                                                                                         
        # The following three registers set the tuning sensitivity.
        si4703.SYS_CONFIG_2.SEEKTH = 19
        si4703.SYS_CONFIG_2.SKSNR = 4
        si4703.SYS_CONFIG_2.SKCNT = 8
        
        si4703.write_registry(self)

        sleep(0.1)

        while si4703.STATUS_RSSI.STC == 0:
            sleep(0.1)
            si4703.update_registry(self)

        si4703.CHANNEL.TUNE = 0
        si4703.write_registry(self)
 
    # This function is mostly for debugging.  It will run for 'timeout' seconds and collect an array of
    # unique groups on a station
    def read_groups(self, timeout):
		
	groups=[None] * 16
	start=time()
	channel=si4703.get_channel(self)
	
	while time()-start<timeout:	
		# Call this first to get the latest values
		si4703.update_registry(self)
		
		if (si4703.STATUS_RSSI.RDSR == 1):
			# We've been tuned while reading this... So reset.
			# There may be a way to do this with the STC bit, but I couldn't
			# get it to work.
			if channel!=si4703.get_channel(self):
				channel=si4703.get_channel(self)
				# start over
				start=time()
				groups=[None] * 16
			
				# building an array of groups. The only point is to easily see which groups 
				# are transmitted during this 5 second interval. Mostly for debugging/enhancements
			if groups[si4703.RDS_B.RDS_B_Group]==None:
				groups[si4703.RDS_B.RDS_B_Group]=si4703.RDS_B.RDS_B_Group

		sleep(0.1)
	print groups

	### Just for group0a, and getting the tuning info
    def read_group0a(self,timeout):
		
		tuning_info = [None] * 4
		comp_array= [False] * 4		
		
		completed=0
		position0a=0

		group0a=0
		old_position0a=-1

		# initial values
		start=time()
		channel=si4703.get_channel(self)

		while time()-start<timeout:

			# Call this first to get the latest values
			si4703.update_registry_ts(self)
			
			# Seeking, just leave. causes issues
			if si4703.POWER_CONFIG.SEEK==1:
				return
			
			# If we tune while we're looping, this will abandon on a weak channel
			# Shouldn't happen when seeking though
			if si4703.STATUS_RSSI.RSS <= si4703.SYS_CONFIG_2.SEEKTH:
				# You can change this to whatever you want. PS should be <= 8 chars though
				si4703.PS=""
				si4703.pty = "Unknown"
				return
			
			# We've been tuned while reading this... So reset.
			# There may be a way to do this with the STC bit, but I couldn't
			# get it to work.
			if channel!=si4703.get_channel(self):
				completed=0
				comp_array= [False] * 4
#				print "Reset due to tuning.(channel check)"
				channel=si4703.get_channel(self)
				# start over
				start=time()
				si4703.PS = ""
				si4703.pty = "Unknown"

			# RDS is ready
			if (si4703.STATUS_RSSI.RDSR==1):
			# Putting this here, even though the function is intended for 0a
			# Group 1A - containes the country code... but I don't think this
			# matter much in the US.  But if it's not the US,then we want to use
			# the dictionary for PTY from EU.
				if si4703.RDS_B.RDS_B_Group == 1 and si4703.RDS_B.RDS_B_Group_Type==0:
					si4703.country = si4703.RDS_B.RDS_B_ECC
#					print "Got country code: " + str(si4703.RDS_B.RDS_B_ECC)
					if si47403.country!=0:
						si4703.ptydict=ptydict_eu
					else:
						si4703.ptydict=ptydict_na
					
				# Group 0A
				if si4703.RDS_B.RDS_B_Group == 0 and si4703.RDS_B.RDS_B_Group_Type==0 and completed<4:
					# Tuning info only.
					group0a=group0a+1
					# If we get a hit, then we'll extend the timeout by 5 seconds
					# The intent is that we can start small, and if we don't get a hit
					# we don't spend a lot of time in here. But if we dom then give it time to
					# get everything
					if group0a==1:
						timeout=timeout+5
						si4703.station_ps[str(channel)]=1
					si4703.pty = si4703.ptydict[si4703.RDS_B.RDS_B_PTY]
					position0a=si4703.RDS_B.RDS_B_Position0A

					if position0a-old_position0a==1 or position0a==0:
						if comp_array[position0a]==False:
							comp_array[position0a]=True
							completed=completed+1
							chr1=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,0,8))
							chr2=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,9,8))
							
							tuning_info[position0a]=chr1+chr2

							old_position0a=position0a
							# We're using this flag, if we get 4 consecutive readings,
							# We have a complete string
							if completed==4:
								si4703.PS=""
								for chrs in tuning_info:
									if chrs!=None:
										si4703.PS=si4703.PS+chrs
								return
							
					if abs(position0a-old_position0a)>1 and completed<4:
#						print "RESET"
						completed=0
						comp_array= [False] * 4
			sleep(.04)

		if group0a==0:
			si4703.PS=""
			si4703.station_ps[str(channel)]=0

    def read_group2a(self, timeout):
		
		song_info = [None] * 16
		
		completed=0
		position2a=0

		group2a=0
		old_position2a=-5
		start=time()
		AB=si4703.RDS_B.RDS_B_AB

		started=False
		record=False
		save_song=False
		
		channel=si4703.get_channel(self)
		
		while time()-start<timeout:
			# call first
			
			si4703.update_registry_ts(self)
			
			# Seeking, just leave. causes issues
			if si4703.POWER_CONFIG.SEEK==1:
				return

			# If we tune while we're looping, this will abandon on a weak channel
			if si4703.STATUS_RSSI.RSS <= si4703.SYS_CONFIG_2.SEEKTH:
				# You can change this to whatever you want. PS should be <= 8 chars though
				si4703.RadioText=""
				si4703.pty = "Unknown"
				return
			
			# We've been tuned while reading this... So reset.
			if channel!=si4703.get_channel(self):
				song_info = [None] * 16
				started=False
#				print "Reset due to tuning.(channel check)"
				channel=si4703.get_channel(self)
				# start over
				start=time()
				si4703.RadioText=""				
			
			if (si4703.STATUS_RSSI.RDSR == 1):
				# Group 2A
				record=False
				
				if si4703.RDS_B.RDS_B_Group == 2 and si4703.RDS_B.RDS_B_Group_Type==0:
					group2a=group2a+1
					if group2a==1:
						# Bump this to 10 seconds
						timeout=timeout+7
						si4703.station_rt[str(channel)]=1
						
					# if the AB flag changed, then reset. This is supposed to mean a programming
					# change.
					if (AB!=si4703.RDS_B.RDS_B_AB):
						AB=si4703.RDS_B.RDS_B_AB
						song_info = [None] * 16
						started=False
#						print "AB change."

					position2a=si4703.RDS_B.RDS_B_Position2A
					# first position
					if started==False:
						started=True						
						firstpos=position2a
						old_position2a=position2a
						record=True

					if position2a-old_position2a==1:
						if position2a==firstpos:
							# we have everything now.
							save_song=True
							break
						record=True
						
					# Use logic to determine if we've wrapped around or if we've
					# missed a reading.
					elif abs(position2a-old_position2a)>1:
						# We're at 0, so we most likely didn't miss a beat,
						# but it would be impossible to know if the we went from 
						# 8->0, and there' a 9th position
						if position2a==0:
							record=True
							# If we started at 0 though, we're done
							if firstpos==0:
								save_song=True
								break
						else:
							started=False
							song_info=[None]*16
							
							
					old_position2a=position2a
					if record==True:
						chr1=chr(si4703.get_reg_value(self,si4703.RDS_C.RDS_C,0,8))
						chr2=chr(si4703.get_reg_value(self,si4703.RDS_C.RDS_C,9,8))					
						chr3=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,0,8))
						chr4=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,9,8))
						song_info[position2a]=chr1+chr2+chr3+chr4						
						
							
			sleep(.04)
				
		## If we got here it's because of a timeout.
		if group2a==0:
			si4703.RadioText=""
			si4703.station_rt[str(channel)]=0
			return
		
		if save_song==True:
			song_str=""
			for chrs in song_info:
				if chrs!=None:
					song_str=song_str+chrs
				
				song_str=song_str.replace('\r', "")
				si4703.RadioText=song_str
			return
		else: # In this condition we have a received a group, but not the whole thing
			si4703.RadioText=""
			return
		
		
			
### This function reads RDS and stores the values in si4703.PS and si4703.RadioText
## It works, and it works fairly well.  However, I decided to go a different direction for my
## applicaiton so I broke groups 0a and 2a into two different functions, intended to be threaded.
## There is also a thread save version of update_registry
    def read_rds(self):
		
		from time import sleep,time
		from datetime import datetime
		
		tuning_info = [None] * 4
		comp_array= [False] * 4		
		song_info = [None] * 16
		
		completed=0
		position0a=0
		position2a=0

		group2a=0
		group0a=0
		old_position0a=-1
		old_position2a=-1		
		start=time()
		AB=0
		PS=False
		SI=False
		duplicate=0
		max_loc=6
		groups=[None] * 16
		
		channel=si4703.get_channel(self)
		## If the signal is less than the seek threshold, we're not going to even bother
		## trying to get RDS data.
		
		if si4703.STATUS_RSSI.RSS <= si4703.SYS_CONFIG_2.SEEKTH:
			# You can change this to whatever you want. PS should be <= 8 chars though
			si4703.PS=""
			si4703.RadioText=""
			si4703.pty = "Unknown"
			return

		while time()-start<10:
			# Seeking, just leave. causes issues
			if si4703.POWER_CONFIG.SEEK==1:
				return
			# We've completed both as best we can tell.
			if SI==True and PS==True:
				return

			# If we tune while we're looping, this will abandon on a weak channel
			if si4703.STATUS_RSSI.RSS <= si4703.SYS_CONFIG_2.SEEKTH:
				# You can change this to whatever you want. PS should be <= 8 chars though
				si4703.PS=""
				si4703.RadioText=""
				si4703.pty = "Unknown"
				return
			
			si4703.update_registry(self)

			# We've been tuned while reading this... So reset.

			if channel!=si4703.get_channel(self):
				completed=0
				comp_array= [False] * 4
				duplicate=0
				song_info = [None] * 16
				print "Reset due to tuning.(channel check)"
				channel=si4703.get_channel(self)
				# start over
				start=time()
				si4703.PS = ""
				si4703.RadioText=""				
			
			# this doesn't seem to work...
			if si4703.CHANNEL.TUNE==1:
				completed=0
				comp_array= [False] * 4
				duplicate=0
				song_info = [None] * 16
				print "Reset due to tuning. (tuning flag)"
				si4703.PS = ""
				si4703.RadioText=""
				sleep(0.1)
				
			# building an array of groups. The only point is to easily see which groups 
			# are transmitted during this 5 second interval. Mostly for debugging/enhancements
			if groups[si4703.RDS_B.RDS_B_Group]==None:
				groups[si4703.RDS_B.RDS_B_Group]=si4703.RDS_B.RDS_B_Group
#				print si4703.RDS_B.RDS_B_Group
			
			if (si4703.STATUS_RSSI.RDSR == 1):
				# Group 2A
				# I'm going to try and make some assumptions about this group being complete
				# Since there is no way to know how long it is.
				if si4703.RDS_B.RDS_B_Group == 2 and si4703.RDS_B.RDS_B_Group_Type==0:
					group2a=group2a+1
					# if the AB flag changed, then reset.
					if (AB!=si4703.RDS_B.RDS_B_AB):
						AB=si4703.RDS_B.RDS_B_AB
				 		completed=0
						comp_array= [False] * 4
						duplicate=0
						song_info = [None] * 16
#						si4703.PS = ""
#						si4703.RadioText=""
#						print "Reset due to AB"
					
					position2a=si4703.RDS_B.RDS_B_Position2A
					chr1=chr(si4703.get_reg_value(self,si4703.RDS_C.RDS_C,0,8))
					chr2=chr(si4703.get_reg_value(self,si4703.RDS_C.RDS_C,9,8))					
					chr3=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,0,8))
					chr4=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,9,8))
					if position2a>max_loc:
						max_loc=position2a
					
					if song_info[position2a]!=None:
						duplicate=duplicate+1
						for index, item in enumerate(song_info):
							SI=True							
							if item==None:
								SI=False
								break
							if index>=max_loc:
#								print "Breaking because all matches"
								break
						if SI==True:
							song_str=""
							for chrs in song_info:
								if chrs!=None:
									song_str=song_str+chrs
									
							song_str=song_str.replace('\r', '\n')
							si4703.RadioText=song_str

					song_info[position2a]=chr1+chr2+chr3+chr4
 					if "\r" in song_info[position2a]:
						max_loc=position2a

				# Group 1A - containes the country code... but I don't think this
				# matter much in the US.  But if it's not the US,then we want to use
				# the dictionary for PTY from EU.
				if si4703.RDS_B.RDS_B_Group == 1 and si4703.RDS_B.RDS_B_Group_Type==0:
					si4703.country = si4703.RDS_B.RDS_B_ECC
					print "Got country code: " + str(si4703.RDS_B.RDS_B_ECC)
					if si47403.country!=0:
						si4703.ptydict=ptydict_eu
					else:
						si4703.ptydict=ptydict_na
					
				# Group 0A
				if si4703.RDS_B.RDS_B_Group == 0 and si4703.RDS_B.RDS_B_Group_Type==0 and PS!=True:
					# Tuning info only.
					group0a=group0a+1
					si4703.pty = si4703.ptydict[si4703.RDS_B.RDS_B_PTY]
					position0a=si4703.RDS_B.RDS_B_Position0A
					if position0a-old_position0a==1 or position0a==0:
						if comp_array[position0a]==False:
							comp_array[position0a]=True
							completed=completed+1
							chr1=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,0,8))
							chr2=chr(si4703.get_reg_value(self,si4703.RDS_D.RDS_D,9,8))
							
							tuning_info[position0a]=chr1+chr2
							
							old_position0a=position0a
							# We're using this flag, if we get 4 consecutive readings, then just stop
							# scanning for this during this function call
							if completed==4:
								PS=True
								si4703.PS=""
								for chrs in tuning_info:
									if chrs!=None:
										si4703.PS=si4703.PS+chrs
								
					if abs(position0a-old_position0a)>1 and PS!=True:
#						print "RESET"
						completed=0
						comp_array= [False] * 4
				
				else:
					sleep(.01)
				#break
				
				
		## If we got here it's because of a timeout.
		if group2a==0:
			si4703.RadioText=""
		if group0a==0:
			si4703.PS=""
		
	### Was exploring RT+  - but let it go.  It's interesting, though.

    def read_rds3a(self):
		from time import sleep,time
		from datetime import datetime
		start=time()
		rtplus_groupid=0
		rtplus_group=0 # Alays zero, I think
		while time()-start<15:
			si4703.update_registry(self)
			if (si4703.STATUS_RSSI.RDSR == 1):
				if rtplus_groupid>0 and si4703.RDS_B.RDS_B_Group == rtplus_group and si4703.RDS_B.RDS_B_Group_Type==rtplus_group:
					# We got an RT+ group
					print
					print "Toggle  : " + str(si4703.RT_PLUS.TOGGLE)
					print "Running : " + str(si4703.RT_PLUS.RUNNING)
					print "Cont 1  : " + str(si4703.RT_PLUS.RT_CONT_1)
					print "Start  1: " + str(si4703.RT_PLUS.START1)
					print "Length 1: " + str(si4703.RT_PLUS.LENGTH1)
					print "Cont 2  : " + str(si4703.RT_PLUS.RT_CONT_2)
					print "Start  2: " + str(si4703.RT_PLUS.START2)
					print "Length 2: " + str(si4703.RT_PLUS.LENGTH2)					
					
				if si4703.RDS_B.RDS_B_Group == 3 and si4703.RDS_B.RDS_B_Group_Type==0:  # Group 3A
					# this indicates RT+
					if format(si4703.RDS_D.RDS_D, 'x')=='4bd7':
						# We've identified a RT+ packet. Now we store the group and ID
						rtplus_groupid=si4703.RDS_B.RDS_B_ApplicationGroupID
						rtplus_group=si4703.RDS_B.RDS_B_ApplicationGroup
						print "App       B: " + str(si4703.RDS_B.RDS_B_ApplicationGroupID)
						print "App       B: " + str(si4703.RDS_B.RDS_B_ApplicationGroup)
						print "ERT        : " + str(si4703.RDS_C.RDS_C_ERT)
						print "Group B: " + str(si4703.RDS_B.RDS_B)
						print "Group C: " + str(si4703.RDS_C.RDS_C)
						print "Group D: " + str(si4703.RDS_D.RDS_D)
						print "Bin   B: " + format(si4703.RDS_B.RDS_B, '#016b')
						print "Bin   C: " + format(si4703.RDS_C.RDS_C, '#016b')
						print "Bin   D: " + format(si4703.RDS_D.RDS_D, '#016b')					
						print "Hex   B: " + format(si4703.RDS_B.RDS_B, 'x')
						print "Hex   C: " + format(si4703.RDS_C.RDS_C, 'x')
						print "Hex   D: " + format(si4703.RDS_D.RDS_D, 'x')					
					
						print "Errors D:" + str(si4703.READ_CHAN.BLER_D)
#					print "Bin: " + format(int("2266", 16), '#016b')
#					print format(int("2266", 16), '#016b')[13:16]
#						print "ASCII B: " + format(si4703.RDS_B.RDS_B, 'x').decode("hex")
#						print "ASCII C: " + format(si4703.RDS_C.RDS_C, 'x').decode("hex")
#						print "ASCII D: " + format(si4703.RDS_D.RDS_D, 'x').decode("hex")
				sleep(.1)
        
    def convert_reg_readings (self, old_registry, reorder):
        '''
        (list, int) ->>> list
        When Python reads  the registry of the si4703 it places all 16 registers into a 32 item list (each item being a single byte). 
        This function gives each register its own item.
        The register at index 0 is 0x0A. If reorder is set to 1, then index 0 will be 0x00. 
        '''
        i = 0
        response = []
        
        while i <=31:
            first_byte = str(bin(old_registry[i]))
            second_byte = str(bin(old_registry[i+1]))
            
            first_byte = first_byte.replace("0b", "", 1)
            second_byte = second_byte.replace("0b", "", 1)

            while len(first_byte) < 8:
                first_byte = "0" + first_byte
            while len(second_byte) < 8:
                second_byte = "0" + second_byte
                
            full_register = first_byte + second_byte
            full_register = int(full_register, 2)
            
            response.append(full_register)
            i += 2
            
        if reorder == 1:
            response = si4703.reorder_reg_readings(self, response)
        return response

    def reorder_reg_readings (self, sixteen_item_list):
        '''
        Since the si4703 starts reading at register 0x0A and wraps back around at 0x0F, the data can be hard to understand.
        This re-orders the data such that the first itme in the list is 0x00, the second item is 0x01.....twelfth item is 0x0C
        '''
        original = sixteen_item_list
        response = []

        ##The item at index 6  is register 0x00
        response.append(original[6])    #0x00
        response.append(original[7])    #0x01
        response.append(original[8])    #0x02
        response.append(original[9])    #0x03
        response.append(original[10])   #0x04
        response.append(original[11])   #0x05
        response.append(original[12])   #0x06
        response.append(original[13])   #0x07
        response.append(original[14])   #0x08
        response.append(original[15])   #0x09
        response.append(original[0])    #0x0A
        response.append(original[1])    #0x0B
        response.append(original[2])    #0x0C
        response.append(original[3])    #0x0D
        response.append(original[4])    #0x0E
        response.append(original[5])    #0x0F

        return response
	# Thread safe version
    def update_registry_ts (self):
		lock=threading.RLock()
		lock.acquire()
		self.update_registry()
		lock.release()
		
    def update_registry (self):
		'''
		This method reads all registers from the Si4703, and stores then into a 32 item array
		Then, it converts the 32 items into a 16-item array (1 item for each of the 16 registers)
		Since for some odd reason the Si4703 always starts reading at 0x0A, this method also reorders the last array such that its first item is 0x00
		Finally this method parses the data into local memory
		'''
		raw_data = []
		cmd = str(si4703.POWER_CONFIG.DSMUTE) + str(si4703.POWER_CONFIG.DMUTE) + str(si4703.POWER_CONFIG.MONO) + "0" + str(si4703.POWER_CONFIG.RDSM) + str(si4703.POWER_CONFIG.SKMODE) + str(si4703.POWER_CONFIG.SEEKUP) + str(si4703.POWER_CONFIG.SEEK)
		cmd = int(cmd, 2)
		try:
			raw_data = si4703.i2c.read_i2c_block_data(0x10,cmd,32)
		except:
			print "Exception in method 'update_registry' while trying to read from si4703"
		reordered_registry = si4703.convert_reg_readings(self, raw_data, 1)

		current_reg = [] 
		## DEVICE_ID					#0x00
		current_reg = reordered_registry[0]
		si4703.DEVICE_ID.PN = si4703.get_reg_value(self, current_reg, 0, 4)
		si4703.DEVICE_ID.MFGID = si4703.get_reg_value(self, current_reg, 4, 12)

		## CHIP_ID					  #0x01
		current_reg = reordered_registry[1]
		si4703.CHIP_ID.REV = si4703.get_reg_value(self, current_reg, 0, 6)
		si4703.CHIP_ID.DEV = si4703.get_reg_value(self, current_reg, 6, 4)
		si4703.CHIP_ID.FIRMWARE = si4703.get_reg_value(self, current_reg, 10, 6)

		## POWER_CONFIG				 #0x02
		current_reg = reordered_registry[2]
		si4703.POWER_CONFIG.DSMUTE = si4703.get_reg_value(self, current_reg, 0, 1)
		si4703.POWER_CONFIG.DMUTE = si4703.get_reg_value(self, current_reg, 1, 1)
		si4703.POWER_CONFIG.MONO = si4703.get_reg_value(self, current_reg, 2, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 3, 1)
		si4703.POWER_CONFIG.RDSM = si4703.get_reg_value(self, current_reg, 4, 1)
		si4703.POWER_CONFIG.SKMODE = si4703.get_reg_value(self, current_reg, 5, 1)
		si4703.POWER_CONFIG.SEEKUP = si4703.get_reg_value(self, current_reg, 6, 1)
		si4703.POWER_CONFIG.SEEK = si4703.get_reg_value(self, current_reg, 7, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 8, 1)
		si4703.POWER_CONFIG.DISABLE = si4703.get_reg_value(self, current_reg, 9, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 10, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 11, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 12, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 13, 1)
		##si4703.POWER_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 14, 1)
		si4703.POWER_CONFIG.ENABLE = si4703.get_reg_value(self, current_reg, 15, 1)

		## CHANNEL					  #0x03
		current_reg = reordered_registry[3]
		si4703.CHANNEL.TUNE = si4703.get_reg_value(self, current_reg, 0, 1)
		##si4703.CHANNEL.UNUSED = si4703.get_reg_value(self, current_reg, 1, 1)
		##si4703.CHANNEL.UNUSED = si4703.get_reg_value(self, current_reg, 2, 1)
		##si4703.CHANNEL.UNUSED = si4703.get_reg_value(self, current_reg, 3, 1)
		##si4703.CHANNEL.UNUSED = si4703.get_reg_value(self, current_reg, 4, 1)
		##si4703.CHANNEL.UNUSED = si4703.get_reg_value(self, current_reg, 5, 1)
		si4703.CHANNEL.CHAN = si4703.get_reg_value(self, current_reg, 6, 10)

		## SYS_CONFIG_1				 0x04
		current_reg = reordered_registry[4]
		si4703.SYS_CONFIG_1.RDSIEN = si4703.get_reg_value(self, current_reg, 0, 1)
		si4703.SYS_CONFIG_1.STCIEN = si4703.get_reg_value(self, current_reg, 1, 1)
		##si4703.SYS_CONFIG_1.UNUSED = si4703.get_reg_value(self, current_reg, 2, 1)
		si4703.SYS_CONFIG_1.RDS = si4703.get_reg_value(self, current_reg, 3, 1)
		si4703.SYS_CONFIG_1.DE = si4703.get_reg_value(self, current_reg, 4, 1)
		si4703.SYS_CONFIG_1.AGCD = si4703.get_reg_value(self, current_reg, 5, 1)
		##si4703.SYS_CONFIG_1.UNUSED = si4703.get_reg_value(self, current_reg, 6, 1)
		##si4703.SYS_CONFIG_1.UNUSED = si4703.get_reg_value(self, current_reg, 7, 1)
		si4703.SYS_CONFIG_1.BLNDADJ = si4703.get_reg_value(self, current_reg, 8, 2)
		si4703.SYS_CONFIG_1.GPIO3 = si4703.get_reg_value(self, current_reg, 10, 2)
		si4703.SYS_CONFIG_1.GPIO2 = si4703.get_reg_value(self, current_reg, 12, 2)
		si4703.SYS_CONFIG_1.GPIO1 = si4703.get_reg_value(self, current_reg, 14, 2)

		## SYS_CONFIG_2				 0x05
		current_reg = reordered_registry[5]
		si4703.SYS_CONFIG_2.SEEKTH = si4703.get_reg_value(self, current_reg, 0, 8)
		si4703.SYS_CONFIG_2.BAND = si4703.get_reg_value(self, current_reg, 8, 2)
		si4703.SYS_CONFIG_2.SPACE = si4703.get_reg_value(self, current_reg, 10, 2)
		si4703.SYS_CONFIG_2.VOLUME = si4703.get_reg_value(self, current_reg, 12, 4)

		## SYS_CONFIG_3				 0x06
		current_reg = reordered_registry[6]
		si4703.SYS_CONFIG_3.SMUTER = si4703.get_reg_value(self, current_reg, 0, 2)
		si4703.SYS_CONFIG_3.SMUTEA = si4703.get_reg_value(self, current_reg, 2, 2)
		##si4703.SYS_CONFIG_3.UNUSED = si4703.get_reg_value(self, current_reg, 4, 1)
		##si4703.SYS_CONFIG_3.UNUSED = si4703.get_reg_value(self, current_reg, 5, 1)
		##si4703.SYS_CONFIG_3.UNUSED = si4703.get_reg_value(self, current_reg, 6, 1)
		si4703.SYS_CONFIG_3.VOLEXT = si4703.get_reg_value(self, current_reg, 7, 1)
		si4703.SYS_CONFIG_3.SKSNR = si4703.get_reg_value(self, current_reg, 8, 4)
		si4703.SYS_CONFIG_3.SKCNT = si4703.get_reg_value(self, current_reg, 12, 4)

		## TEST_1					   0x07
		current_reg = reordered_registry[7]
		si4703.TEST_1.XOSCEN = si4703.get_reg_value(self, current_reg, 0, 1)
		si4703.TEST_1.AHIZEN = si4703.get_reg_value(self, current_reg, 1, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 2, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 3, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 4, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 5, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 6, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 7, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 8, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 9, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 10, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 11, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 12, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 13, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 14, 1)
		##si4703.TEST_1.UNUSED = si4703.get_reg_value(self, current_reg, 15, 1)

		## TEST_2					   0x08		ALL BITS UNUSED
		current_reg = reordered_registry[8]
		##si4703.TEST_2.UNUSED = si4703.get_reg_value(self, current_reg, 0, 16)

		## BOOT_CONFIG				  0x09		ALL BITS UNUSED
		current_reg = reordered_registry[9]
		##si4703.BOOT_CONFIG.UNUSED = si4703.get_reg_value(self, current_reg, 0, 16)

		## STATUS_RSSI				  0x0A
		current_reg = reordered_registry[10]
		si4703.STATUS_RSSI.RDSR = si4703.get_reg_value(self, current_reg, 0, 1)
		si4703.STATUS_RSSI.STC = si4703.get_reg_value(self, current_reg, 1, 1)
		si4703.STATUS_RSSI.SFBL = si4703.get_reg_value(self, current_reg, 2, 1)
		si4703.STATUS_RSSI.AFCRL = si4703.get_reg_value(self, current_reg, 3, 1)
		si4703.STATUS_RSSI.RDSS = si4703.get_reg_value(self, current_reg, 4, 1)
		si4703.STATUS_RSSI.BLER_A = si4703.get_reg_value(self, current_reg, 5, 2)
		si4703.STATUS_RSSI.ST = si4703.get_reg_value(self, current_reg, 7, 1)
		si4703.STATUS_RSSI.RSS = si4703.get_reg_value(self, current_reg, 8, 8)

		## READ_CHAN					0x0B
		current_reg = reordered_registry[11]
		si4703.READ_CHAN.BLER_B = si4703.get_reg_value(self, current_reg, 0, 2)
		si4703.READ_CHAN.BLER_C = si4703.get_reg_value(self, current_reg, 2, 2)
		si4703.READ_CHAN.BLER_D = si4703.get_reg_value(self, current_reg, 4, 2)
		si4703.READ_CHAN.READ_CHAN = si4703.get_reg_value(self, current_reg, 6, 10)

		## RDS_A						0x0C
		current_reg = reordered_registry[12]
		si4703.RDS_A.RDS_A = si4703.get_reg_value(self, current_reg, 0, 16)
		

		## RDS_B						0x0D
		current_reg = reordered_registry[13]
        # Variables for Group 0A/2B
		si4703.RDS_B.RDS_B = si4703.get_reg_value(self, current_reg, 0, 16)
		si4703.RDS_B.RDS_B_Group = si4703.get_reg_value(self, current_reg, 0, 4)			# Added to capture the group number
		si4703.RDS_B.RDS_B_Group_Type = si4703.get_reg_value(self, current_reg, 4, 1)		 # Added to capture the group type
		si4703.RDS_B.RDS_B_Traffic = si4703.get_reg_value(self, current_reg, 5, 1)		 # Traffic flag
		si4703.RDS_B.RDS_B_PTY = si4703.get_reg_value(self, current_reg, 6, 5)			   # Added to capture the PTY number

		
		# Just for Group 0A
		si4703.RDS_B.RDS_B_Music = si4703.get_reg_value(self, current_reg, 12, 1)		 # Music or speech
		si4703.RDS_B.RDS_B_Position0A = si4703.get_reg_value(self, current_reg, 13, 3)		 # position of text
		
        # Variables for Group 2A 
		si4703.RDS_B.RDS_B_AB = si4703.get_reg_value(self, current_reg, 11, 1)		 # position of text
		si4703.RDS_B.RDS_B_Position2A = si4703.get_reg_value(self, current_reg, 12, 4)		 # position of text

		# Just for group 3A
		si4703.RDS_B.RDS_B_ApplicationGroupID = si4703.get_reg_value(self, current_reg, 12, 4)		 
		si4703.RDS_B.RDS_B_ApplicationGroup = si4703.get_reg_value(self, current_reg, 15, 1)

		# Country code from 1A
		si4703.RDS_B.RDS_B_ECC = si4703.get_reg_value(self, current_reg, 8,8)
		
		
		## RDS_C						0x0E
		current_reg = reordered_registry[14]
		si4703.RDS_C.RDS_C = si4703.get_reg_value(self, current_reg, 0, 16)
		si4703.RDS_C.ERT   = si4703.get_reg_value(self, current_reg, 2, 1)
		## RDS_D						0x0F
		current_reg = reordered_registry[15]
		si4703.RDS_D.RDS_D = si4703.get_reg_value(self, current_reg, 0, 16)

		## This is all for RT+
		## https://tech.ebu.ch/docs/techreview/trev_307-radiotext.pdf
		## The specific data for RT+ does not fall into the above 16 bit categories.
		## So, we need to take pieces of Group B, Group C, and Group D and make them into the data bits we need.
		## I'm not sure of the best way to do this, so we'll convert to binary strings, and then back.
		
		## Toggle and running bit are in the second group of 16 bits ("B")
		si4703.RT_PLUS.TOGGLE=si4703.get_reg_value(self, reordered_registry[13], 11, 1)
		si4703.RT_PLUS.RUNNING=si4703.get_reg_value(self, reordered_registry[13], 12, 1)
		
		## RT Content 1 lies in both group "B" and group "C"
		content1_int=si4703.get_reg_value(self, reordered_registry[13], 13, 3)
		content2_int=si4703.get_reg_value(self, reordered_registry[14], 0, 3)
		content1_strb=format(content1_int, "#b").replace("0b","")
		content2_strb=format(content2_int, "#b").replace("0b","")
		rt_content=content1_strb+content2_strb
		si4703.RT_PLUS.RT_CONT_1=int(rt_content,2)
		
		si4703.RT_PLUS.START1=si4703.get_reg_value(self, reordered_registry[14], 3, 6)
		si4703.RT_PLUS.LENGTH1=si4703.get_reg_value(self, reordered_registry[14], 9, 6)

		## RT Content 3 lies in both group "C" and group "D"
		content1_int=si4703.get_reg_value(self, reordered_registry[14], 15, 1)
		content2_int=si4703.get_reg_value(self, reordered_registry[15], 0, 5)
		content1_strb=format(content1_int, "#b").replace("0b","")
		content2_strb=format(content2_int, "#b").replace("0b","")
		rt_content=content1_strb+content2_strb
		si4703.RT_PLUS.RT_CONT_2=int(rt_content,2)
		
		si4703.RT_PLUS.START1=si4703.get_reg_value(self, reordered_registry[15], 5, 6)
		si4703.RT_PLUS.LENGTH1=si4703.get_reg_value(self, reordered_registry[14], 11, 5)
		
		
    def get_reg_value(self, register, begin, length):
        
        #This class continually has to copy the contents of the Si4703's registers to the Pi's internal memory. This function helps parse the data from the Si4703.
        #In order to parse the data, we need the raw data, along with the location of a property and its length in bits (ie READCHAN's location would be index 6 and its length would be 9 bits)

        #Internally, Python converts any hex, octal, or binary number into an integer for storage. This is why the register is represented as an integer at first. We then convert it to a string of nothing but 1s and 0s, and add extra zeros until it is 16 bits long.
        #After doing this, we can use the location and length information to return the value of a property.
        
        int_register = register                        ##give this a friendlier name
        str_register = str(bin(int_register))          ##Convert the register to a string (ie 15 becomes "0b1111") 
        str_register = str_register.replace("0b", "")  ##Get rid of the "0b" prefix (ie 15 would now become "1111") 
        while len(str_register) < 16:                  ##We want the output to be 16 bits long 
            str_register = "0" + str_register          ##Add preceeding zeros until it IS 16 characters long
        response = str_register[begin : begin + length]##Weed out all the bits we don't need
        response = int(response, 2)                    ##Convert it back to an assignable integer
        
        return response

    def write_registry(self):
        '''
        Refreshes the registers on the device with the ones stored in local memory on the Pi.
        It will only refresh the registers 0x02-07, as all other registers cannot be written to
        '''
        main_list = []
        crazy_first_number = 0
        
        first_byte = 0
        second_byte = 0

        ## POWER_CONFIG                 #0x02
        first_byte = str(si4703.POWER_CONFIG.DSMUTE) + str(si4703.POWER_CONFIG.DMUTE) + str(si4703.POWER_CONFIG.MONO) + "0" + str(si4703.POWER_CONFIG.RDSM) + str(si4703.POWER_CONFIG.SKMODE) + str(si4703.POWER_CONFIG.SEEKUP) + str(si4703.POWER_CONFIG.SEEK)
        second_byte = "0" + str(si4703.POWER_CONFIG.DISABLE) + "00000" + str(si4703.POWER_CONFIG.ENABLE)
        first_byte = int(first_byte, 2)
        crazy_first_number = first_byte
        second_byte = int(second_byte, 2)
        main_list.append(second_byte)

        ## CHANNEL                      #0x03
        first_byte = str(si4703.CHANNEL.TUNE) + "0000000"
        second_byte =si4703.return_with_padding(self, si4703.CHANNEL.CHAN, 10)
        first_byte = int(first_byte, 2)
        second_byte = int(second_byte, 2)
        main_list.append(first_byte)
        main_list.append(second_byte)

        ## SYS_CONFIG_1                 0x04
        first_byte = str(si4703.SYS_CONFIG_1.RDSIEN) + str(si4703.SYS_CONFIG_1.STCIEN) + "0" + str(si4703.SYS_CONFIG_1.RDS) + str(si4703.SYS_CONFIG_1.DE) + str(si4703.SYS_CONFIG_1.AGCD) + "00"
        second_byte = si4703.return_with_padding(self, si4703.SYS_CONFIG_1.BLNDADJ, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_1.GPIO3, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_1.GPIO2, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_1.GPIO1, 2)
        first_byte = int(first_byte, 2)
        second_byte = int(second_byte, 2)
        main_list.append(first_byte)
        main_list.append(second_byte)

        ## SYS_CONFIG_2                 0x05
        first_byte = si4703.return_with_padding(self, si4703.SYS_CONFIG_2.SEEKTH, 8)
        second_byte = si4703.return_with_padding(self, si4703.SYS_CONFIG_2.BAND, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_2.SPACE, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_2.VOLUME, 4)
        first_byte = int(first_byte, 2)
        second_byte = int(second_byte, 2)
        main_list.append(first_byte)
        main_list.append(second_byte)

        ## SYS_CONFIG_3                 0x06
        first_byte = si4703.return_with_padding(self, si4703.SYS_CONFIG_3.SMUTER, 2) + si4703.return_with_padding(self, si4703.SYS_CONFIG_3.SMUTEA, 2) + "000" + str(si4703.SYS_CONFIG_3.VOLEXT)
        second_byte = si4703.return_with_padding(self, si4703.SYS_CONFIG_3.SKSNR, 4) + si4703.return_with_padding(self, si4703.SYS_CONFIG_3.SKCNT, 4)
        first_byte = int(first_byte, 2)
        second_byte = int(second_byte, 2)
        main_list.append(first_byte)
        main_list.append(second_byte)
        
        ## TEST_1                       0x07
        if si4703.TEST_1.POWER_SEQUENCE == 55:   ##Since all but the first two bits in this register are unused, and we only write to this to power up/down the device, it seems unessary to write this registry every time. Especially considering that writing 0 to the remaining register while in operation can prove fatal
            first_byte = str(si4703.TEST_1.XOSCEN) + str(si4703.TEST_1.AHIZEN) + si4703.return_with_padding(self, si4703.TEST_1.RESERVED_FIRST_BYTE, 4)
            second_byte = si4703.return_with_padding(self, si4703.TEST_1.RESERVED_SECOND_BYTE, 8)
            first_byte = int(first_byte, 2)
            second_byte = int(second_byte, 2)
            main_list.append(first_byte)
            main_list.append(second_byte)
        if si4703.TEST_1.POWER_SEQUENCE == True:##debug code for TEST_1. remove after debugging
            main_list.append(129) 

		### - commented out this ###
        #print main_list
        #print crazy_first_number
		
        w6 = si4703.i2c.write_i2c_block_data(0x10, crazy_first_number, main_list)
        si4703.update_registry(self)

    def return_with_padding (self, item_as_integer, length):
        item_as_integer = str(bin(item_as_integer))
        item_as_integer = item_as_integer.replace("0b", "")

        while len(item_as_integer) < length:
            item_as_integer = "0" + item_as_integer

        return item_as_integer
    def tune (self, frequency):
        '''
        Frequency (Mhz) (ie 98.5 tunes to 98.5; 104.5 tunes to 104.5)
        The si4703 doesn't use verbatim tuning. Such that you cannot tune to 104.5 by setting CHAN to 1045.
        Instead, setting CHAN to 0 will tune to the lowest frequency allowable for your region. Your region is set by setting BAND.
        Setting CHAN to 1 will tune to the lowest frequency allowable + spacing
        ie
        BAND = 0        ## 87.5-108.0 (default)
        SPACE = 0       ## 200 Khz (default)
        CHAN = 1
        The tuned frequency would be 87.7
        '''
        from time import sleep, time
        
        frequency = float(frequency)
        channel = 0
        spacing = 0

        if si4703.SYS_CONFIG_2.SPACE == 0:  # Typical spacing for USA & Australia (default) - 200 Khz or 0.2 Mhz
            spacing = 20
        elif si4703.SYS_CONFIG_2.SPACE == 1:# Typical spacing for Europe & Japan            - 100 Khz or 0.1 Mhz
            spacing = 10
        elif si4703.SYS_CONFIG_2.SPACE == 3:# Minimum spacing allowed                       -  50 Khz or 0.05 Mhz
            spacing = 5
            
        if si4703.SYS_CONFIG_2.BAND == 0:   # 87.5-108.0 Mhz for USA/Europe
            channel = ((frequency*100)-8750)/spacing
        else:                               # 76.0-108.0 Mhz(Japan wide-band) or 76.0-90.0 Mhz (Japan)
            channel = ((frequency*100)-7600)/spacing # These fall into the same if statement because the begining of the bands both start at 76.0 Mhz

        channel = int(channel)              #We turned this into a float earlier for some proper division, so we better turn it back to an int before we try to write it

        si4703.CHANNEL.TUNE = 1             #Must set the TUNE bit in order to perform a tune 
        si4703.CHANNEL.CHAN = channel       #Also, we need to tell it what to tune to
        si4703.write_registry(self)         #Now write all of this to the si4703

        si4703.wait_for_tune(self)
            
        si4703.CHANNEL.TUNE = 0             #In order to do anything else, we have to clear the TUNE bit once the device successfully (or unsuccessfully for that matter) tuned
        si4703.write_registry(self)
	
	# Clear these out for RDS so that when we retune they become blank
	si4703.PS=""
	si4703.RadioText=""

    def wait_for_tune (self):
        from time import sleep, time
        
        begining_time = time()
        
        while si4703.STATUS_RSSI.ST == 0:   #The si4703 sets the ST bit high whenever it is finished tuning/seeking
            if time() - begining_time > 0.9:  #If we've been in this loop for more than two seconds, then get out
                break
            sleep(0.1)                      #This is only precautionary. We don't want to overload anything by reading/writing over and over and back to back
            si4703.update_registry(self)

    def seek_right (self):
        '''
        Seeks to the closest station above the currently tuned station.
        '''
        si4703.update_registry(self)
        
        si4703.POWER_CONFIG.SEEKUP = 1
        si4703.POWER_CONFIG.SEEK = 1
        si4703.write_registry(self)

        si4703.wait_for_tune(self)

        si4703.POWER_CONFIG.SEEK = 0
        si4703.write_registry(self)
    def seek_left (self):
        '''
        Seeks to the closest station below the currently tuned station.
        '''
        si4703.update_registry(self)
        
        si4703.POWER_CONFIG.SEEKUP = 0
        si4703.POWER_CONFIG.SEEK = 1
        si4703.write_registry(self)

        si4703.wait_for_tune(self)

        si4703.POWER_CONFIG.SEEK = 0
        si4703.write_registry(self)

	
    def get_channel (self):
        '''
        get_channel() ->> float
        Returns the frequency currenly tuned to
        Since the CHAN property is only a valid property after a tune operation and not a seek operation, we must use the READ_CHAN property to get the frequency
        Also, just like CHAN, the frequency isn't verbatim and is encoded somewhat such that if READ_CHAN = 0 then the frequency is the lowest possible frequency for the reciever
        '''
        channel = si4703.READ_CHAN.READ_CHAN
        spacing = 0
        frequency = 0.0

        if si4703.SYS_CONFIG_2.SPACE == 0:  # Typical spacing for USA & Australia (default) - 200 Khz or 0.2 Mhz
            spacing = 20
        elif si4703.SYS_CONFIG_2.SPACE == 1:# Typical spacing for Europe & Japan            - 100 Khz or 0.1 Mhz
            spacing = 10
        elif si4703.SYS_CONFIG_2.SPACE == 3:# Minimum spacing allowed                       -  50 Khz or 0.05 Mhz
            spacing = 5
            
        if si4703.SYS_CONFIG_2.BAND == 0:   # 87.5-108.0 Mhz for USA/Europe
            frequency = (((channel * spacing) + 8750) / 100.0)
        else:                               # 76.0-108.0 Mhz(Japan wide-band) or 76.0-90.0 Mhz (Japan)
            frequency = (((channel * spacing) + 8750) / 100.0)# These fall into the same if statement because the begining of the bands both start at 76.0 Mhz
        return frequency

    def toggle_mute (self):
        '''
        Toggles the mute feature. The si4703 is muted by default once the device is enabled.
        Changing the mute feature is done by chaning the Disable Mute property (DMUTE)
        '''
        if si4703.POWER_CONFIG.DMUTE == 0:  
            si4703.POWER_CONFIG.DMUTE = 1
        else:
            si4703.POWER_CONFIG.DMUTE = 0
        
        si4703.write_registry(self)
    def volume (self, volume):
        '''
        Int must be a integer no lower than 0 and no higher than 15
        '''
        if 0 <= volume <= 15:   ## Did the user provide a proper value between 0 and 15?
            pass
        elif volume < 0:        ## Well at this point they didn't give us a good volume integer, so we're going to mute it if it's too low
            volume = 0
        else:                   ## And in the last case, where it is too high, we'll set it to the highest possible setting
            volume = 15
            
        si4703.SYS_CONFIG_2.VOLUME = volume ## Finally, let's save all that work
        si4703.write_registry(self)          ## And then write it in stone

    def tune_left (self):
        '''
        Analogous to a tuning dial, this tunes to the next available frequency on the left of the current station. 
        '''
        current_channel = si4703.get_channel(self)
        if si4703.SYS_CONFIG_2.SPACE == 0:
            current_channel -= 0.2
        elif si4703.SYS_CONFIG_2 == 1:
            current_channel -= 0.1
        else:
            current_channel -= 0.05

        si4703.tune(self, current_channel)
    def tune_right (self):
        '''
        Analogous to a tuning dial, this tunes to the next available frequency on the right of the current station. 
        '''
        current_channel = si4703.get_channel(self)
        if si4703.SYS_CONFIG_2.SPACE == 0:
            current_channel += 0.2
        elif si4703.SYS_CONFIG_2 == 1:
            current_channel += 0.1
        else:
            current_channel += 0.05

        si4703.tune(self, current_channel)
    def print_registry(self):
        print"POWER_CONFIG:"
        print"\t", "DSMUTE:", si4703.POWER_CONFIG.DSMUTE
        print"\t", "DMUTE:", si4703.POWER_CONFIG.DMUTE
        print"\t", "MONO:", si4703.POWER_CONFIG.MONO
        print"\t", "RDSM:", si4703.POWER_CONFIG.RDSM
        print"\t", "SKMODE:", si4703.POWER_CONFIG.SKMODE
        print"\t", "SEEKUP:", si4703.POWER_CONFIG.SEEKUP
        print"\t", "SEEK:", si4703.POWER_CONFIG.SEEK
        print"\t", "DISABLE:", si4703.POWER_CONFIG.DISABLE
        print"\t", "ENABLE:", si4703.POWER_CONFIG.ENABLE
        
        print"CHANNEL:"
        print"\t", "TUNE:", si4703.CHANNEL.TUNE 
        fmchan = si4703.CHANNEL.CHAN
        fmchan = (((fmchan*20)+8750)/10)
        print"\t", "CHAN:", si4703.CHANNEL.CHAN, "(", fmchan, ")"
        
        print"SYS_CONFIG_1:"
        print"\t", "RDSIEN:", si4703.SYS_CONFIG_1.RDSIEN
        print"\t", "STCIEN:", si4703.SYS_CONFIG_1.STCIEN
        print"\t", "RDS:", si4703.SYS_CONFIG_1.RDS
        print"\t", "DE:", si4703.SYS_CONFIG_1.DE
        print"\t", "AGCD:", si4703.SYS_CONFIG_1.AGCD
        print"\t", "BLNDADJ:", si4703.SYS_CONFIG_1.BLNDADJ
        print"\t", "GPIO3:", si4703.SYS_CONFIG_1.GPIO3
        print"\t", "GPIO2:", si4703.SYS_CONFIG_1.GPIO2
        print"\t", "GPIO1:", si4703.SYS_CONFIG_1.GPIO1
        
        print"SYS_CONFIG_2"
        print"\t", "SEEKTH:", si4703.SYS_CONFIG_2.SEEKTH
        print"\t", "BAND:", si4703.SYS_CONFIG_2.BAND
        print"\t", "SPACE:", si4703.SYS_CONFIG_2.SPACE
        print"\t", "VOLUME:", si4703.SYS_CONFIG_2.VOLUME
        
        print"SYS_CONFIG_3"
        print"\t", "SMUTER:", si4703.SYS_CONFIG_3.SMUTER
        print"\t", "SMUTEA:", si4703.SYS_CONFIG_3.SMUTEA
        print"\t","VOLEXT:", si4703.SYS_CONFIG_3.VOLEXT
        print"\t", "SKSNR:", si4703.SYS_CONFIG_3.SKSNR
        print"\t", "SKCNT:", si4703.SYS_CONFIG_3.SKCNT
        print"TEST_1"
        print"\t", "XOSCEN:", si4703.TEST_1.XOSCEN
        print"\t", "AHIZEN:", si4703.TEST_1.AHIZEN
        print"\t", "RESERVED_FIRST_BYTE:", si4703.TEST_1.RESERVED_FIRST_BYTE
        print"\t", "RESERVED_SECOND_BYTE:", si4703.TEST_1.RESERVED_SECOND_BYTE
      
    class DEVICE_ID:                    #0x00
        PN     = 0
        MFGID  = 0
    class CHIP_ID:                      #0x01
        REV    = 0
        DEV    = 0
        FIRMWARE=0
    class POWER_CONFIG:                 #0x02
        DSMUTE = 0
        DMUTE  = 0
        MONO   = 0
        ##     = 0
        RDSM   = 0
        SKMODE = 0
        SEEKUP = 0
        SEEK   = 0
        ##     = 0
        DISABLE= 0
        ##     = 0
        ##     = 0
        ##     = 0
        ##     = 0
        ##     = 0
        ENABLE = 0
        def FULL_REGISTER (self):  
            first_byte = str(DSMUTE) + str(DMUTE) + str(MONO) + "0" + str(RDSM) + str(SKMODE) + str(SEEKUP) + str(SEEK)
            first_byte = int(first_byte, 2)
            
            second_byte = "0" + str(DISABLE) + "00000" + str(ENABLE)
            second_byte = int(second_byte, 2)
            return [first_byte, second_byte]

    class CHANNEL:                      #0x03
        TUNE   = 0
        ##     = 0
        ##     = 0
        ##     = 0
        ##     = 0
        ##     = 0
        CHAN   = 0
    class SYS_CONFIG_1:                 #0x04
        RDSIEN = 0
        STCIEN = 0
        ##     = 0
        RDS    = 0
        DE     = 0
        AGCD   = 0
        ##     = 0
        ##     = 0
        BLNDADJ= 0
        GPIO3  = 0
        GPIO2  = 0
        GPIO1  = 0
    class SYS_CONFIG_2:                 #0x05
        SEEKTH = 0
        BAND   = 0
        SPACE  = 0
        VOLUME = 0
    class SYS_CONFIG_3:                 #0x06
        SMUTER = 0
        SMUTEA = 0
        ##     =
        ##     =
        ##     = 0
        VOLEXT = 0
        SKSNR  = 0
        SKCNT  = 0
    class TEST_1:                       #0x07
        XOSCEN = 0
        AHIZEN = 0
        RESERVED_FIRST_BYTE = 0 ## These bits are reserved, but their reset values are known, so they must be set-able 
        RESERVED_SECOND_BYTE = 0
        POWER_SEQUENCE = False
    class TEST_2:                       #0x08
        TEST_2 = 0
        ##ALL BITS IN THIS REGISTER ARE UNUSED
    class BOOT_CONFIG:                  #0x09
        BOOT_CONFIG = 0
        ##ALL BITS IN THIS REGISTER ARE UNUSED
    class STATUS_RSSI:                  #0x0A
        RDSR   = 0
        STC    = 0
        SFBL   = 0
        AFCRL  = 0
        RDSS   = 0
        BLER_A = 0
        ST     = 0
        RSSI   = 0
    class READ_CHAN:                    #0x0B
        BLER_B = 0 ##SEE THE STATUS_RSI REGISTER ABOVER FOR BLER-A
        BLER_C = 0
        BLER_D = 0
        READ_CHAN = 0
    class RDS_A:                        #0x0C
		RDS_A  = 0
    class RDS_B:                        #0x0D
		RDS_B  = 0
		RDS_B  = 0
		RDS_B_Group = 0
		RDS_B_Group_Type = 0
		RDS_B_PTY = 0
		RDS_B_Traffic = 0
		RDS_B_AB = 0  # music or speaking bit
		RDS_B_Position = 0  # Position of the string
		RDS_B_ECC = 0
    class RDS_C:                        #0x0E
        RDS_C  = 0
        RDS_C_ERT = 0
    class RDS_D:                        #0x0F
        RDS_D  = 0
    class RT_PLUS:
		TOGGLE=0
		RUNNING=0
		RT_CONT_1=0
		START1=0
		LENGTH1=0
		RT_CONT_2=0
		START2=0
		LENGTH2=0

    