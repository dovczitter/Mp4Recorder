from kivymd.app import MDApp
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivy.uix.floatlayout import FloatLayout
from kivy.factory import Factory
from kivy.properties import ObjectProperty
from kivy.uix.popup import Popup
from kivy.utils import platform
from kivy.utils import get_color_from_hex
from kivymd.color_definitions import colors
from kivy.lang import Builder

import time
from datetime import datetime, timezone
from os.path import basename, isfile
from jnius import autoclass
from recorder import Recorder

import socket

# ----------------- NOTE NOTE NOTE -------------------
# ----------------- NOTE NOTE NOTE -------------------
# ----------------- NOTE NOTE NOTE -------------------
# to import modified style.kv: https://stackoverflow.com/questions/52812576/how-to-customize-style-kv-in-kivy
# https://stackoverflow.com/questions/40090453/font-color-of-filechooser?rq=3
#
import kivy
from kivy.lang import Builder
import os 
Builder.unload_file(os.path.join(kivy.__file__, '../data/style.kv'))
Builder.load_file('./style.kv')
# ----------------- NOTE NOTE NOTE -------------------
# ----------------- NOTE NOTE NOTE -------------------
# ----------------- NOTE NOTE NOTE -------------------

# =========== WIP how to keep kivy android screen on python example
# =========== WIP : https://stackoverflow.com/questions/63218114/how-to-keep-kivy-service-running-in-background-in-android-service-still-run-whe
# =========== WIP see: \\wsl.localhost\Ubuntu\home\dovczitter\Mp4Recorder\.buildozer\android\platform\build-armeabi-v7a\dists\mp4recorderapp\jni\SDL\android-project\app\src\main\AndroidManifest.xml

# See buildozer : #android.activity_class_name = org.kivy.android.PythonActivity
#

# camera: https://kivy.org/doc/stable/examples/gen__camera__main__py.html
# video recorder: https://stackoverflow.com/questions/62063847/is-there-a-way-to-record-videos-in-kivy
# https://www.programcreek.com/python/?code=codelv%2Fenaml-native%2Fenaml-native-master%2Fsrc%2Fenamlnative%2Fandroid%2Fapp.py#

# https://www.geeksforgeeks.org/how-to-keep-the-device-screen-on-in-android/
#

__version__ = 7.0
mp4Recorder = ''
loadFilename = None
emailFileMsg = ''
# Note: 'LoadDialog' filters listing with 'Log' in filename
log_root_filename = 'Mp4Recorder'
isCheckwifi = False

# ============================================
#               Mp4Recorder
# ============================================
class Mp4Recorder(MDBoxLayout):

    # https://stackoverflow.com/questions/58591221/kivy-attribute-error-object-has-no-attribute-trying-to-connect-widgets-in-kv
    state = ObjectProperty()

    def __init__(self, **kwargs):
        if not platform == "android":
            print('========== ERROR : not android platform ==============')
            return

        from android.permissions import request_permissions, Permission

        global __version__
        global mp4Recorder
        global loadFilename
        global emailFileMsg
        
        self.logMsgCount = 0

        # WIP:
        # https://search.yahoo.com/yhs/search?hspart=mnet&hsimp=yhs-001&type=type9085796-spa-3537-84480&param1=3537&param2=84480&p=kivy+android+not+changing+button+color+python
        #  https://www.geeksforgeeks.org/change-button-color-in-kivy/
        # good: https://www.youtube.com/watch?v=2IuAQ1HUpU4
        # color code picker: https://htmlcolorcodes.com/
        #                    https://htmlcolorcodes.com/color-names/

        self.color_red    = get_color_from_hex('#ff0000')
        self.color_orange = get_color_from_hex('#fbb800')
        self.color_green  = get_color_from_hex('#008000')
        self.color_yellow = get_color_from_hex('#ffee33')

        self.time_label_color = self.color_orange
        self.record_button_color = self.color_orange
        self.email_button_color = self.color_orange
        self.emailfile_button_color = self.color_orange
        self.checkwifi_button_color = self.color_orange
        self.exit_button_color = self.color_orange

        self.time_label_text = '00:00:00'
        self.record_button_text = 'START Recording'
        self.email_button_text = 'Email [No recording to email]'
        self.emailfile_button_text = 'Email File'
        self.checkwifi_button_text = 'CheckWifi -DISABLED-'
        self.exit_button_text = 'Exit'

        self.wifiBlink = False
        self.recordBlink = False
        self.recordFilename = ''
        self.recordSeconds = 0
        self.mp4Version = __version__
        self.email_ok2send = False
        self.logFp = None
        self.permissions_external_storage_complete = False
        
        super(Mp4Recorder, self).__init__(**kwargs)
       
        #
        # 'request_permissions' first, waits in background until 'permissions_external_storage'
        # is complete. Then allows for the request respons, then continues with kivy. 
        print('========== BEFORE init request_permissions ==============')
        request_permissions([Permission.RECORD_AUDIO, Permission.ACCESS_WIFI_STATE, Permission.INTERNET])
        print('========== AFTER  init request_permissions ==============')
      
        # https://programtalk.com/vs4/python/adywizard/car-locator/main.py/
        # https://github.com/kivy/plyer/issues/661
        print('========== BEFORE init permissions_external_storage ==============')
        self.permissions_external_storage()
        print('========== AFTER  init permissions_external_storage ==============')

        mp4Recorder = Recorder()

        self.state = 'ready'

        self.time_started = False
        
        # ------------ ScrollView stuff. ie 'Info' -----------------
        self.sv = ScrollView()
        self.ml = MDList()
        self.sv.add_widget(self.ml)
                     
        self.file_choose_root = Root()
        
        self.start_time()

    # ---------------------------------------------
    #            permissions_external_storage
    # ---------------------------------------------
    def permissions_external_storage(self, *args):  
        # https://github.com/kivy/plyer/issues/661                
        if platform == "android":
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Environment = autoclass("android.os.Environment")
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")

            # If you have access to the external storage, do whatever you need
            if Environment.isExternalStorageManager():
                # If you don't have access, launch a new activity to show the user the system's dialog
                # to allow access to the external storage
                print('=================== Environment.isExternalStorageManager() pass ==========================')
                pass
            else:
                try:
                    from typing import cast
                    activity = PythonActivity.mActivity.getApplicationContext()
                    uri = Uri.parse("package:" + activity.getPackageName())
                    intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, uri)
                    currentActivity = cast(
                    "android.app.Activity", PythonActivity.mActivity
                    )
                    currentActivity.startActivityForResult(intent, 101)
                except:
                    intent = Intent()
                    intent.setAction(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION)
                    currentActivity = cast(
                    "android.app.Activity", PythonActivity.mActivity
                    )
                    currentActivity.startActivityForResult(intent, 101) 

        self.permissions_external_storage_complete = True
                    
    # ---------------------------------------------
    #                   timer
    # ---------------------------------------------
    def timer(self, *args):
        global mp4Recorder
        global loadFilename
        global emailFileMsg

        # -------- wifi -----------
        self.check_wifi()

        time_str = f'''[Mp4Recorder {self.mp4Version}]\n[{time.asctime()}]'''
        
        # -------- record -----------
        
        if self.state == 'recording':
            # Regular time convert routines generate timezone issues
            # Decided to do this with simple per second math.
            self.recordSeconds = self.recordSeconds + 1
            
            hrs = int(self.recordSeconds / 3600)
            min = int(self.recordSeconds / 60)
            sec = int(self.recordSeconds - (hrs*3600 + min*60))
            
            RecordingTime = f'{hrs:02d}:{min:02d}:{sec:02d}'
            self.ids.record_button.text = f'''STOP Recording [{RecordingTime}]\n{mp4Recorder.get_mp4_filename()}'''

            if self.recordBlink:
                self.recordBlink = False
                self.ids.record_button.md_bg_color = self.color_green
            else:
                self.recordBlink = True
                self.ids.record_button.md_bg_color = self.color_orange
        else:
            self.recordSeconds = 0  
            self.recordBlink = False         

        self.ids.time_label.text = f'''\n{time_str}\n[{self.checkwifi_text}]\n'''

        if loadFilename != None:
            self.update_labels()

    # ---------------------------------------------
    #            start_time
    # ---------------------------------------------
    def start_time(self):
        Clock.schedule_interval(self.timer, 1)

    # ---------------------------------------------
    #            wifiCheck
    # ---------------------------------------------
    def wifiCheck(self):
        # https://stackoverflow.com/questions/3764291/how-can-i-see-if-theres-an-available-and-active-network-connection-in-python
        host="8.8.8.8"  # Google's public domain server
        port=53
        timeout=0.5     # Half second float timeout

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except socket.error as ex:
            #print(ex)
            return False
            
    # ---------------------------------------------
    #            check_wifi
    # ---------------------------------------------
    def check_wifi(self):
        global isCheckwifi

        if isCheckwifi:
            chk = ''
            if self.wifiCheck():
                chk = '* UP *'
                self.email_ok2send = True
            else:
                chk = '- DN -'
                self.email_ok2send = False
                if self.wifiBlink:
                    self.wifiBlink = False                
                else:
                    self.wifiBlink = True
            self.checkwifi_text = f'Wifi {chk}'
        else:
            self.checkwifi_text = self.ids.checkwifi_button.text
            self.wifiBlink = False
            self.email_ok2send = True

        return self.email_ok2send

    # ---------------------------------------------
    #            logMessage
    # ---------------------------------------------
    def logMessage(self, msg):
        global log_root_filename

        now = datetime.now()
        dt_string = now.strftime("%d%b%Y:%H:%M:%S")

        if self.logFp == None:
            # Note, dt_tag is valid per install, a re-install would clear cache file.
            # Use HMS for re-install case. 
#           dt_tag = now.strftime("%d%b%Y")
            dt_tag = now.strftime("%d%b%Y_%H%M%S")
            log_filename = f'{log_root_filename}_{dt_tag}.log'
            self.LogPath = log_filename
            print(f'========== log_filename: {log_filename}, LogPath: {self.LogPath}')
            if isfile(self.LogPath):
                print(f'================ isfile TRUE [{self.LogPath}]  ================')
                self.logFp = open(self.LogPath,'a+')
            else:
                print(f'================ isfile FALSE [{self.LogPath}]  ================')
                self.logFp = open(self.LogPath,'w+')
            startmsg = f'[{dt_string}]  ========= {log_root_filename} {self.mp4Version} =========\n'
            self.logFp.write(startmsg)
            self.logFp.flush()

        logmsg = f'''[{dt_string}]\n{msg}'''

        self.logFp.write(logmsg)
        self.logFp.flush()
      
        mp4Recorder.file_copy(self.LogPath)

        print(logmsg)
        
        # Show in ScrollView, current at top.
        txt = f'[{dt_string}] {msg}'
        self.ids.container.add_widget(OneLineListItem(text = txt),index=self.logMsgCount)
        self.logMsgCount = self.logMsgCount + 1

    # ---------------------------------------------
    #            record
    # ---------------------------------------------
    def record(self):
        global mp4Recorder

        # 'record() will toggle state from 'ready' to 'recording' to 'ready'

        old_fn = mp4Recorder.get_mp4_filename()
        old_basefn = basename(old_fn)

        self.state = mp4Recorder.record(self.state)

        cur_fn = mp4Recorder.get_mp4_filename()
        cur_basefn = basename(cur_fn)

        if self.state == 'ready':                        
            self.ids.email_button.text = f'''Email Recording\n{old_basefn}'''
            self.logMessage(f'''Recording complete, {old_basefn}.''')
        else:
            self.logMessage(f'''Recording started, {cur_basefn}.''')

        self.update_labels()

    # ---------------------------------------------
    #            email
    # ---------------------------------------------
    def email(self):
        global mp4Recorder

        msg = self.ids.email_button.text
        if self.state != 'ready':
            self.logMessage(f'{self.ids.email_button.text}: Recording in progress.')
            self.update_labels()
            return
                
        recordFilename = mp4Recorder.get_mp4_filename()
        if recordFilename == '':
            self.ids.email_button.text = self.email_button_text
            msg = self.ids.email_button.text
        else:
            fn = basename(recordFilename)
            if self.email_ok2send:
                # Absolute wifi check, independant of 'isCheckwifi' flag.
                if self.wifiCheck():
                    self.ids.email_button.text = f'''Emailing\n{fn}'''
                    msg = mp4Recorder.email(recordFilename)
                    mp4Recorder.clear_mp4_filename()
                    self.ids.email_button.text = self.email_button_text
                else:
                    self.ids.email_button.text = f'''Email\n{fn}'''
                    msg = f'{self.emailfile_button_text} *ERROR* WiFi down, check system, try again. '
            else:
                msg = f'{self.emailfile_button_text} *ERROR* [WiFi DN] Cannot email'

        self.logMessage(msg)
        self.update_labels()

    # ---------------------------------------------
    #            emailfile
    # ---------------------------------------------
    def emailfile(self):
        msg = ''
        if self.state != 'ready':
            self.logMessage(f'{self.ids.emailfile_button.text} Recording in progress.')
            self.update_labels()
            return
        
        # ------------------------------------------------------------------------
        # Root emailfile class will do the actual filechoose and email.
        # See show_load() stuff.
        # 'loadFilename' reported in timer() via update_labels() when available.
        # ------------------------------------------------------------------------
        
        # Absolute wifi check, independant of 'isCheckwifi' flag.
        if self.wifiCheck():
            if self.email_ok2send:
                self.file_choose_root.show_load()
                msg = f'{self.ids.emailfile_button.text}: File choose complete'
            else:
                msg = f'{self.ids.emailfile_button.text}: *[WiFi DN]* Cannot EmailFile.'
        else:
            msg = f'{self.ids.emailfile_button.text}: *ERROR* WiFi down, check system, try again.'

        self.logMessage(msg)            
        self.update_labels()

    # ---------------------------------------------
    #            checkwifi
    # ---------------------------------------------
    def checkwifi(self):
        global isCheckwifi

        chk = '-DISABLED-'
        isCheckwifi = not isCheckwifi
        if isCheckwifi: chk='*ENABLED*'

        msg = f'CheckWifi {chk}'
        self.ids.checkwifi_button.text = msg
        self.logMessage(msg)            
        self.update_labels()

    # ---------------------------------------------
    #            exit
    # ---------------------------------------------
    def exit(self):
        global mp4Recorder

        if self.state == 'recording':
            recordFilename = mp4Recorder.get_mp4_filename()
            basefn = basename(recordFilename)
            self.logMessage(f'Saving {basefn}')
            self.state = mp4Recorder.record(self.state)

        self.logMessage(self.ids.exit_button.text)
        # Close logfile.
        self.logFp.close()
        mp4Recorder.file_copy(self.LogPath)
        mp4Recorder.exit()

    # ---------------------------------------------
    #            update_labels
    # ---------------------------------------------
    def update_labels(self):
        global mp4Recorder
        global loadFilename
        global emailFileMsg
        global isCheckwifi

        recordFilename = mp4Recorder.get_mp4_filename()
        basefn = basename(recordFilename)

        # --------- Button label updates --------
        if self.state == 'ready':
            self.ids.record_button.md_bg_color = self.color_orange
            self.ids.record_button.text = self.record_button_text

        if self.state == 'recording':
            self.ids.record_button.md_bg_color = self.color_green

        # -------- Email and EmailFile updates
        if self.email_ok2send:
            self.ids.time_label.color = "orange"

            if self.state == 'recording':
                self.ids.email_button.text = "Email [Stop Recording]"
                self.ids.emailfile_button.text = "Email File [Stop Recording]"
            else:
                self.ids.emailfile_button.text = "Email File"
        else:
            if isCheckwifi:
                self.ids.email_button.text = "No Email [WiFi DN]"
                self.ids.emailfile_button.text = "No Email File [WiFi DN]"
                if self.wifiBlink:
                    self.ids.time_label.color = "white"
                else:
                    self.ids.time_label.color = "red"
            else:
                self.ids.email_button.text = "No Email"
                self.ids.emailfile_button.text = "Email File"

        if loadFilename != None: 
            basefn = basename(loadFilename)
            end_msg = f'[Email File Complete : {basefn}] '
            self.logMessage(end_msg)
            # NOTE - clear local loadFilename, generates only one update per load.
            loadFilename = None
            
# =============================================
#               LoadDialog
# =============================================
class LoadDialog(FloatLayout):

    def __init__(self, **kwargs):
        super(LoadDialog, self).__init__(**kwargs)

    # Note - exclude logfiles.
        
    def sort_by_date(files, filesystem):    
        import os  

        return (sorted(f for f in files if filesystem.is_dir(f)) +
            sorted((f for f in files if not filesystem.is_dir(f) and not 'Log' in f), key=lambda fi: os.stat(fi).st_mtime, reverse = True))

    def sort_by_name(files, filesystem):
        return (sorted(f for f in files if filesystem.is_dir(f)) +
            sorted((f for f in files if not filesystem.is_dir(f) and not 'Log' in f), reverse = True))

    default_sort_func = ObjectProperty(sort_by_date)
          
    emailfile = ObjectProperty(None)
    cancel = ObjectProperty(None)
    sort = ObjectProperty(None)
    
# =============================================
#            Root
# =============================================
class Root(FloatLayout):
    
    def __init__(self, **kwargs):
        super(Root, self).__init__(**kwargs)
        self.content = None

    # ---------------------------------------------
    #            dismiss_popup
    # ---------------------------------------------
    def dismiss_popup(self):
        self._popup.dismiss()

    # ---------------------------------------------
    #            show_load
    # ---------------------------------------------
    def show_load(self):
        global mp4Recorder
        global loadFilename
        global emailFileMsg

        self.content = LoadDialog(emailfile=self.emailfile, cancel=self.dismiss_popup)
        print(f'=========== show_load path [{mp4Recorder.get_mp4_path()}] ==========')
        self.content.ids.filechooser.path = mp4Recorder.get_mp4_path()

        self._popup = Popup(title="Load file", content=self.content, size_hint=(0.9, 0.9))
        self._popup.open()

    # ---------------------------------------------
    #            emailfile
    # ---------------------------------------------
    def emailfile(self, path, selection):
        global mp4Recorder
        global loadFilename
        global emailFileMsg
                
        msg = ''
        try:
            loadFilename = selection[0]
            if isfile(loadFilename):
                emailFileMsg = mp4Recorder.email(loadFilename)
            else:
                emailFileMsg = f'Email File error, file [{loadFilename}] does not exist'
            self.dismiss_popup()
        except:
            pass
    
# =============================================
#            Mp4RecorderApp
# =============================================
class Mp4RecorderApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"
        return Mp4Recorder()

Factory.register('Root', cls=Root)
Factory.register('LoadDialog', cls=LoadDialog)

if __name__ == '__main__':
    
    Mp4RecorderApp().run()
