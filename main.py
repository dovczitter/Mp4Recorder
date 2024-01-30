from kivymd.app import MDApp
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.scrollview import ScrollView
from kivymd.uix.list import MDList, OneLineListItem
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


"""
Currently using external program to keep screen active. Any reason why you cant add in your code something like this
android:keepScreenOn = “true”
https://www.geeksforgeeks.org/how-to-keep-the-device-screen-on-in-android/
another reference
https://www.stechies.com/keep-screen-stay-awake-android-app/
"""

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

__version__ = 4.4
mp4Recorder = ''
loadFilename = None
emailFileMsg = ''
# Note: 'LoadDialog' filters listing with 'Log' in filename
log_root_filename = 'Mp4RecorderLog'
msgList = []

# ============================================
#               Mp4Recorder
# ============================================
class Mp4Recorder(MDBoxLayout):
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
        
#       self.wifiBlink = False
        self.wifi_str = 'CheckWifi'
        self.recordSeconds = 0
        self.mp4Version = __version__
        self.email_ok2send = False
        self.logFp = None
        self.permissions_external_storage_complete = False

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
            self.ids.record_button.text = f'''Recording [{RecordingTime}]\n{mp4Recorder.get_mp4_filename()}'''
        else:
            self.recordSeconds = 0           

        self.ids.time_label.text = f'''\n{time_str}\n[{self.wifi_str}]\n'''
        
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
        from ping3 import ping
        # https://github.com/kyan001/ping3
        # UP rsp : 0.016164541244506836
        # DN rsp : None
        rsp = ping('google.com', timeout=1)
        return isinstance(rsp, float)

    # ---------------------------------------------
    #            check_wifi
    # ---------------------------------------------
    def check_wifi(self):
        chk = ''
        if self.wifiCheck():
            chk = '* UP *'
            self.ids.time_label.color = "orange"
            self.email_ok2send = True
        else:
            chk = '- DN -'
            self.email_ok2send = False
            if self.wifiBlink:
                self.ids.time_label.color = "white"
                self.wifiBlink = False                
            else:
                self.ids.time_label.color = "red"
                self.wifiBlink = True
        self.wifi_str = f'Wifi {chk}'
        return self.email_ok2send

    # ---------------------------------------------
    #            logMessage
    # ---------------------------------------------
    def logMessage(self, msg):
        global log_root_filename
        global msgList

        now = datetime.now()
        dt_string = now.strftime("%d%b%Y:%H:%M:%S")

        if self.logFp == None:
            dt_tag = now.strftime("%d%b%Y")
            log_filename = f'{log_root_filename}_{dt_tag}.mp4'
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

        logmsg = f'[{dt_string}] {msg}\n'
        self.logFp.write(logmsg)
        self.logFp.flush()

        mp4Recorder.file_copy(self.LogPath)

        print(logmsg)

        self.ids.container.add_widget(OneLineListItem(text=logmsg))

        # Generate a reverse ordered view, current at top of list.
#        msgList.append(logmsg)
#        items = msgList.copy()
#        items.reverse()
#        self.ids.container.clear_widgets()
#        for item in items:
#            self.ids.container.add_widget(OneLineListItem(text=item))
    
#    # ---------------------------------------------
#    #            get_state
#    # ---------------------------------------------
#    def get_state(self):
#        return self.state
    
    # ---------------------------------------------
    #            record
    # ---------------------------------------------
    def record(self):
        global mp4Recorder
        self.logMessage(self.ids.record_button.text)
        self.state = mp4Recorder.record(self.state)
        self.update_labels()

    # ---------------------------------------------
    #            email
    # ---------------------------------------------
    def email(self):
        global mp4Recorder

        self.logMessage(self.ids.email_button.text)
        msg = ''
        if self.state != 'ready':
            self.logMessage('Recording in progress.')
            self.update_labels()
            return
        
        if self.email_ok2send:
            recordFilename = mp4Recorder.get_mp4_filename()
            msg = mp4Recorder.email(recordFilename)
        else:
            msg = f'******* [WiFi DN] Cannot Email {recordFilename} ********'

        self.logMessage(msg)
        self.update_labels()

    # ---------------------------------------------
    #            emailfile
    # ---------------------------------------------
    def emailfile(self):
        msg = ''
        self.logMessage(self.ids.emailfile_button.text)
        
        if self.state != 'ready':
            self.logMessage('Recording in progress.')
            self.update_labels()
            return
        
        # ------------------------------------------------------------------------
        # Root emailfile class will do the actual filechoose and email.
        # See show_load() stuff.
        # 'loadFilename' reported in timer() via update_labels() when available.
        # ------------------------------------------------------------------------
        if self.email_ok2send:
            self.file_choose_root.show_load()
            msg = 'File choose complete'
        else:
            msg = f'******* [WiFi DN] Cannot EmailFile ********'

        self.logMessage(msg)            
        self.update_labels()

    # ---------------------------------------------
    #            exit
    # ---------------------------------------------
    def exit(self):
        global mp4Recorder
        self.logMessage(self.ids.exit_button.text)
        # === testing ===
#       mp4Recorder.file_copy(self.LogPath)
        mp4Recorder.exit()

    # ---------------------------------------------
    #            update_labels
    # ---------------------------------------------
    def update_labels(self):
        global mp4Recorder
        global loadFilename
        global emailFileMsg

        # --------- Button label updates --------
        if self.state == 'ready':
            self.ids.record_button.background_normal = ''
            self.ids.record_button.background_color = self.color_orange
            self.ids.record_button.text = 'START Recording'

        if self.state == 'recording':
            self.ids.record_button.background_normal = ''
            self.ids.record_button.background_color = self.color_green

        # -------- Email and EmailFile updates
        if self.email_ok2send:

            if self.state == 'recording':
                self.ids.email_button.background_normal = ''
                self.ids.email_button.background_color = self.color_yellow
                self.ids.email_button.text = "Email [Stop Recording]"

                self.ids.emailfile_button.background_normal = ''
                self.ids.emailfile_button.background_color = self.color_yellow
                self.ids.emailfile_button.text = "Email File [Stop Recording]"
            else:
                self.ids.email_button.background_normal = ''
                self.ids.email_button.background_color = self.color_orange
                self.ids.email_button.text = "Email"

                self.ids.emailfile_button.background_normal = ''
                self.ids.emailfile_button.background_color = self.color_orange
                self.ids.emailfile_button.text = "Email File"
        else:
            self.ids.email_button.background_normal = ''
            self.ids.email_button.background_color = self.color_red
            self.ids.email_button.text = "No Email [WiFi DN]"
            self.ids.emailfile_button.background_normal = ''
            self.ids.emailfile_button.background_color = self.color_red
            self.ids.emailfile_button.text = "No Email File [WiFi DN]"

        recordFilename = mp4Recorder.get_mp4_filename()
        if isfile(recordFilename):
            basefn = basename(recordFilename)
            end_msg = f'[Audio : {self.state}] [Recorded File : {basefn}] '
            self.logMessage(end_msg)

        if loadFilename != None: 
            basefn = basename(loadFilename)
            end_msg = f'[Email File : {basefn}] '
            self.logMessage(end_msg)
            # NOTE - clear loacal loadFilename, generates only one update per load.
            loadFilename = None
            
# =============================================
#               LoadDialog
# =============================================
class LoadDialog(FloatLayout):

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

        content = LoadDialog(emailfile=self.emailfile, cancel=self.dismiss_popup)
        print(f'=========== show_load path [{mp4Recorder.get_mp4_path()}] ==========')
        content.ids.filechooser.path = mp4Recorder.get_mp4_path()

        self._popup = Popup(title="Load file", content=content, size_hint=(0.9, 0.9))
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

# https://stackoverflow.com/questions/40090453/font-color-of-filechooser?rq=3

from kivy.lang import Builder

if __name__ == '__main__':
    
    Mp4RecorderApp().run()
