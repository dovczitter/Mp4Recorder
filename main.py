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
from kivy.properties import StringProperty
from kivymd.color_definitions import colors
import time

from os.path import basename,exists
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

__version__ = '2.6'
mp4Recorder = ''
loadFilename = ''
emailFileMsg = ''
check_wifi_flag = False

# ============================================
#               Mp4Recorder
# ============================================
class Mp4Recorder(MDBoxLayout):

    def __init__(self, **kwargs):
        
        if not platform == "android":
            # ===== ToDo: Log an error =========
            return

        from android.permissions import request_permissions, Permission

        global __version__
        global mp4Recorder
        global loadFilename
        global emailFileMsg

        self.wifiBlink = False
        self.recordSeconds = 0
        self.mp4Version = __version__
        self.email_ok2send = False

        # WIP:
        # https://search.yahoo.com/yhs/search?hspart=mnet&hsimp=yhs-001&type=type9085796-spa-3537-84480&param1=3537&param2=84480&p=kivy+android+not+changing+button+color+python
        #  https://www.geeksforgeeks.org/change-button-color-in-kivy/
        # good: https://www.youtube.com/watch?v=2IuAQ1HUpU4
        # color code picker: https://htmlcolorcodes.com/
        #                    https://htmlcolorcodes.com/color-names/

        self.color_red    = get_color_from_hex('#ff0000')
        self.color_orange = get_color_from_hex('#fbb800')
        self.color_green  = get_color_from_hex('#008000')

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
        self.contacts = []
                     
        self.file_choose_root = Root()
        
        rsp = self.wifiCheck()
        print(f'after self.wifiCheck(), [{rsp}]')
        
        self.start_time()

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
                    
    # ---------------------------------------------
    #                   timer
    # ---------------------------------------------
    def timer(self, *args):
        global mp4Recorder
        global loadFilename
        global emailFileMsg
        global check_wifi_flag

        from time import gmtime, strftime
        from datetime import datetime, timezone
        
        chk = ''
        wifi_str = ''
        # -------- TODO - log transition ----------- 
        # -------- wifi -----------
        if check_wifi_flag:
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
            wifi_str = f'Wifi {chk}'

        time_str = f'''[Mp4Recorder {self.mp4Version}]\n[{time.asctime()}]'''
        
        # -------- record -----------
        
        if self.state == 'recording':
            # Regular time convert routines generate timezone issues
            # Decided to do this with simple per second math.
            self.recordSeconds = self.recordSeconds + 1
            
            hrs = int(self.recordSeconds / 3600)
            min = int(self.recordSeconds / 60)
            sec = int(self.recordSeconds - (hrs*3600 + min*60))
            
            diffStr = f'{hrs:02d}:{min:02d}:{sec:02d}'
            
            mp4Fn = mp4Recorder.get_mp4_filename()
            
            time_str = f'''[{mp4Fn}]\n[RecordingTime: {diffStr}]'''

        else:
            self.recordSeconds = 0           
        if check_wifi_flag:
            self.ids.time_label.text = f'''\n{time_str}\n[{wifi_str}]\n'''
        else:
            self.ids.time_label.text = f'''\n{time_str}\n'''
        
        if self.email_ok2send:
            self.ids.email_button.background_normal = ''
            self.ids.email_button.background_color = self.color_orange
            self.ids.email_button.text = "Email"

            self.ids.emailfile_button.background_normal = ''
            self.ids.emailfile_button.background_color = self.color_orange
            self.ids.emailfile_button.text = "Email File"

        else:
            self.ids.email_button.background_normal = ''
            self.ids.email_button.background_color = self.color_red
            self.ids.email_button.text = "No Email [Check WiFi]"
            self.ids.emailfile_button.background_normal = ''
            self.ids.emailfile_button.background_color = self.color_red
            self.ids.emailfile_button.text = "No Email File [Check WiFi]"

        if exists(loadFilename):
            self.update_labels()
    #
    # -------- start_time -------
    #
    def start_time(self):
        Clock.schedule_interval(self.timer, 1)

    #
    # -------- wifiCheck -------
    #
    def wifiCheck(self):
        from ping3 import ping
        # https://github.com/kyan001/ping3
        # UP rsp : 0.016164541244506836
        # DN rsp : None
        rsp = ping('google.com', timeout=1)
        return isinstance(rsp, float)
    #
    # -------- LogMessage ------- WIP -----
    #
    def LogMessage(self, msg):
        from datetime import datetime
        
        now = datetime.now()
        dt_string = now.strftime("%d%b%Y_%H%M%S")
        
        logmsg = f'[{dt_string}] {msg}'

        self.ids.container.add_widget(
            OneLineListItem(text=logmsg)
        )
        self.sv.scroll_to(logmsg)
    
    # ======================
    #       record 
    # ======================
    def record(self):
        global mp4Recorder
        self.state = mp4Recorder.record(self.state)
        self.update_labels()

    # ======================
    #       email 
    # ======================
    def email(self):
        global mp4Recorder
        msg = ''
        if self.state != 'ready':
            msg = 'Recording in progress.'
        else:
            if self.email_ok2send:
                recordFilename = mp4Recorder.get_mp4_filename()
                print(f'================= recordFilename [{recordFilename}] ====================')
                msg = mp4Recorder.email(recordFilename)
        
        self.LogMessage(msg)
        
        self.update_labels()

    # ======================
    #       emailfile 
    # ======================
    def emailfile(self):
        if self.state != 'ready':
            self.LogMessage('Recording in progress.')
            self.update_labels()
            return
        
        # ------------------------------------------------------------------------
        # Root emailfile class will do the actual filechoose and email.
        # See show_load() stuff.
        # 'loadFilename' reported in timer() via update_labels() when available.
        # ------------------------------------------------------------------------
        self.file_choose_root.show_load()
            
        self.update_labels()

    # ======================
    #       check_wifi 
    # ======================
    def check_wifi(self):
        global check_wifi_flag

        if check_wifi_flag:
            self.ids.wifi_button.background_normal = ''
            self.ids.wifi_button.background_color = self.color_orange
            check_wifi_flag = False
        else:
            self.ids.wifi_button.background_normal = ''
            self.ids.wifi_button.background_color = self.color_green
            check_wifi_flag = True

    # ======================
    #       exit 
    # ======================
    def exit(self):
        global mp4Recorder
        mp4Recorder.exit()

    # ======================
    #       update_labels
    # ======================
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
            self.ids.record_button.text = 'STOP Recording'

        # -------- Email and EmailFile updates
        recordFilename = mp4Recorder.get_mp4_filename()
        if exists(recordFilename):
            basefn = basename(recordFilename)
            end_msg = f'[Audio : {self.state}] [Recorded File : {basefn}] '
            self.LogMessage(end_msg)

        if exists(loadFilename):
            basefn = basename(loadFilename)
            end_msg = f'[Email File : {basefn}] '
            self.LogMessage(end_msg)
            # NOTE - clear loacal loadFilename, generates only one update per load.
            loadFilename = ''
            
# ============================================
#               LoadDialog
# ============================================
class LoadDialog(FloatLayout):
    
    def sort_by_date(files, filesystem):    
        import os
        return (sorted(f for f in files if filesystem.is_dir(f)) +
            sorted((f for f in files if not filesystem.is_dir(f)), key=lambda fi: os.stat(fi).st_mtime, reverse = True))
        
    def sort_by_name(files, filesystem):
        return (sorted(f for f in files if filesystem.is_dir(f)) +
                sorted(f for f in files if not filesystem.is_dir(f))) 
        
    default_sort_func = ObjectProperty(sort_by_date)
          
    emailfile = ObjectProperty(None)
    cancel = ObjectProperty(None)
    sort = ObjectProperty(None)
    
# ============================================
#               Root
# ============================================
class Root(FloatLayout):

    #
    # -------- dismiss_popup --------
    #
    def dismiss_popup(self):
        self._popup.dismiss()

    #
    # -------- show_popup --------
    #
    def show_load(self):
        global mp4Recorder
        global loadFilename
        global emailFileMsg

        content = LoadDialog(emailfile=self.emailfile, cancel=self.dismiss_popup)
        print(f'=========== show_load path [{mp4Recorder.get_mp4_path()}] ==========')
        content.ids.filechooser.path = mp4Recorder.get_mp4_path()

        self._popup = Popup(title="Load file", content=content, size_hint=(0.9, 0.9))
        self._popup.open()
 
    #
    # -------- emailfile --------
    #
    def emailfile(self, path, selection):
        global mp4Recorder
        global loadFilename
        global emailFileMsg
                
        msg = ''
        try:
            loadFilename = selection[0]
            if exists(loadFilename):
                emailFileMsg = mp4Recorder.email(loadFilename)
            else:
                emailFileMsg = f'Email File error, file [{loadFilename}] does not exist'
            self.dismiss_popup()
        except:
            pass
        
class Mp4RecorderApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"
        return Mp4Recorder()

Factory.register('Root', cls=Root)
Factory.register('LoadDialog', cls=LoadDialog)

if __name__ == '__main__':
    
    Mp4RecorderApp().run()
