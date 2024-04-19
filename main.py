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
from kivy import platform
from kivy.event import EventDispatcher

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

__version__ = 8.0
mp4Recorder = ''
emailFileMsg = ''
emilFileCancelMsg = f'EmailFile was CANCELED'

# Note: 'LoadDialog' filters listing with 'Log' in filename
log_root_filename = 'Mp4Recorder'

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
        global emailFileMsg

        self.logMsgCount = 0

        self.color_red    = get_color_from_hex('#ff0000')
        self.color_orange = get_color_from_hex('#fbb800')
        self.color_green  = get_color_from_hex('#008000')
        self.color_yellow = get_color_from_hex('#ffee33')

        self.time_label_color = self.color_orange
        self.record_button_color = self.color_orange
        self.email_button_color = self.color_orange
        self.emailfile_button_color = self.color_orange
        self.reset_button_color = self.color_orange
        self.exit_button_color = self.color_orange

        self.time_label_text = '00:00:00'
        self.record_button_text = 'START Recording'
        self.email_button_text = 'Email [No recording to email]'
        self.emailfile_button_text = 'EmailFile'
        self.reset_button_text = 'Reset'
        self.exit_button_text = 'Exit'

        self.resetBlink = False
        self.recordBlink = False
        self.recordSeconds = 0
        self.timeSeconds = 0
        self.mp4Version = __version__
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
        self.ids.emailfile_button.disabled = False

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
        global emailFileMsg
        global emilFileCancelMsg

        isWifi = self.wifiCheck()
        time_str = f'''[Mp4Recorder {self.mp4Version}]\n[{time.asctime()}]'''
        wifi_str = 'WiFi is UP' if isWifi else 'WiFi is !*DOWN*!'
        self.ids.time_label.text = f'''\n{time_str}\n[{wifi_str}]\n'''

        email_text = self.email_button_text if isWifi else 'Email - wifi *DOWN*'
        emailfile_text = self.emailfile_button_text if isWifi else 'EmailFile - wifi *DOWN*'

        if self.state != 'ready':
            self.ids.emailfile_button.disabled = True

        # Handle a cancelled EmailFile notification
        if emailFileMsg == emilFileCancelMsg:
            emailFileMsg = ''
            mp4Recorder.clear_emailfile_filename()
            self.logMessage('EmailFile was CANCELLED')

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

            self.ids.email_button.text = email_text
            self.ids.emailfile_button.text = emailfile_text

            if self.recordBlink:
                self.recordBlink = False
                self.ids.record_button.md_bg_color = self.color_green
            else:
                self.recordBlink = True
                self.ids.record_button.md_bg_color = self.color_orange
        else:
            self.recordSeconds = 0  
            self.recordBlink = False 

            mp4FileName = mp4Recorder.get_mp4_filename()
            emailFileName = mp4Recorder.get_emailfile_filename()

            if mp4FileName != '':
                baseFn = basename(mp4FileName)
                if mp4Recorder.isEmailProcess():
                    self.ids.email_button.text = f'''Email ...Sending... :\n[{baseFn}]'''
                else:
                    self.ids.email_button.text = f'''Email :\n[{baseFn}]'''

            elif emailFileName != '':
                baseFn = basename(emailFileName)
                self.ids.emailfile_button.text = f'''EmailFile ...Sending... :\n[{baseFn}]'''

            else:
                self.ids.email_button.disabled = False
                self.ids.email_button.text = email_text

                self.ids.emailfile_button.disabled = False
                self.ids.emailfile_button.text = emailfile_text

                mp4Recorder.clearEmailProcess()

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

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except socket.error as ex:
            #print(ex)
            return False
            
    # ---------------------------------------------
    #            logMessage
    # ---------------------------------------------
    def logMessage(self, msg):
        global log_root_filename

        now = datetime.now()
        dt_string = now.strftime("%d%b%Y:%H:%M:%S")

        if self.logFp == None:
            # Note, dt_tag is valid per install, a re-install would clear cache file.
            # Use HMS for next day re-install case. 
            # dt_tag = now.strftime("%d%b%Y")
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

        # 'mp4Recorder.record() will toggle state from 'ready' to 'recording' to 'ready'

        old_fn = mp4Recorder.get_mp4_filename()
        old_basefn = basename(old_fn)

        # Will START or STOP recording based on current record state.
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

        msg = ''
        if self.state != 'ready':
            self.logMessage(f'{self.ids.email_button.text}: Recording in progress.')
            self.update_labels()
            return

        mp4FileName = mp4Recorder.get_mp4_filename()
        if mp4FileName == '':
            self.ids.email_button.text = f'{self.email_button_text} NO recording to email'
            msg = self.ids.email_button.text
        else:
            fn = basename(mp4FileName)
            if self.wifiCheck():
                print(f'###### ------------- BEFORE mp4Recorder.email({mp4FileName}) -----------------------------------------')
                print(f'###### ------------- BEFORE mp4Recorder.email({mp4FileName}) -----------------------------------------')
                print(f'###### ------------- BEFORE mp4Recorder.email({mp4FileName}) -----------------------------------------')
                mp4Recorder.email(mp4FileName)
                print(f'###### ------------- AFTER  mp4Recorder.email({mp4FileName}) -----------------------------------------')
                print(f'###### ------------- AFTER  mp4Recorder.email({mp4FileName}) -----------------------------------------')
                print(f'###### ------------- AFTER  mp4Recorder.email({mp4FileName}) -----------------------------------------')
                # timer() will update emil button 
            else:
                self.ids.email_button.text = f'''Email - wifi was down,try again.\n{fn}'''
                msg = f'{self.emailfile_button_text} *ERROR* WiFi down, check system, try again. '

        if msg != '':
            self.logMessage(msg)
        self.update_labels()

    # ---------------------------------------------
    #            emailfile
    # ---------------------------------------------
    def emailfile(self):
        global emailFileMsg
        global mp4Recorder

        msg = ''
        if self.state != 'ready':
            self.logMessage(f'{self.ids.emailfile_button.text} Recording in progress.')
            self.update_labels()
            return
        
        # ------------------------------------------------------------------------
        # Root emailfile class will do the actual filechoose and email.
        # See show_load() stuff.
        # 'emilfileName' reported in timer() via update_labels() when available.
        # ------------------------------------------------------------------------
        
        # Prevent multi EmailFile button hits while sending large files.
        emailFileName = mp4Recorder.get_emailfile_filename()
        if emailFileName != '':
            self.logMessage(f'{self.ids.emailfile_button.text} EmailFile in progress.')
            self.update_labels()
            return
            
        # Absolute wifi check.
        if self.wifiCheck():
            emailFileMsg = ''
            # timer() will update email and emailfile buttons.
            # 'emailFileName' is set in show_load()
            print(f'###### -------------------- emailfile(): Before self.file_choose_root.show_load() --------------------')
            print(f'###### -------------------- emailfile(): Before self.file_choose_root.show_load() --------------------')
            print(f'###### -------------------- emailfile(): Before self.file_choose_root.show_load() --------------------')
            self.file_choose_root.show_load()
            print(f'###### -------------------- emailfile(): After self.file_choose_root.show_load() --------------------')
            print(f'###### -------------------- emailfile(): After self.file_choose_root.show_load() --------------------')
            print(f'###### -------------------- emailfile(): After self.file_choose_root.show_load() --------------------')
        else:
            msg = f'{self.ids.emailfile_button.text}: Wifi is DOWN'

        if msg != '':
            self.logMessage(msg)            
        self.update_labels()

    # ---------------------------------------------
    #            reset
    # ---------------------------------------------
    def reset(self):
        global emailFileMsg
        global isEmailFile
        global mp4Recorder

        if self.state == 'recording':
            # Issue a STOP recording.
            self.record()

        emailFileMsg = ''
        isEmailFile = False
        self.timeSeconds = 0
        mp4Recorder.clear_emailfile_filename()
        mp4Recorder.clear_mp4_filename()
        mp4Recorder.clearEmailProcess()

        self.ids.record_button.text = self.record_button_text
        self.ids.email_button.text = self.email_button_text
        self.ids.emailfile_button.text = self.emailfile_button_text
        self.ids.reset_button.text = self.reset_button_text
        self.ids.exit_button.text = self.exit_button_text
        
        self.ids.record_button.disabled = False
        self.ids.email_button.disabled = False
        self.ids.emailfile_button.disabled = False
        self.ids.reset_button.disabled = False
        self.ids.exit_button.disabled = False   
           
        wifichk = 'UP' if self.wifiCheck() else '!*DOWN*!'
        self.logMessage(f'Reset complete, wifi is {wifichk}')            
        self.update_labels()
        
    # ---------------------------------------------
    #            exit
    # ---------------------------------------------
    def exit(self):
        global mp4Recorder

        if self.state == 'recording':
            mp4FileName = mp4Recorder.get_mp4_filename()
            basefn = basename(mp4FileName)
            self.logMessage(f'Saving {basefn}')
            self.state = mp4Recorder.record(self.state)

        self.logMessage(self.ids.exit_button.text)
        # Close logfile.
        self.logFp.close()
        mp4Recorder.file_copy(self.LogPath)
        quit()
        
    # ---------------------------------------------
    #            update_labels
    # ---------------------------------------------
    def update_labels(self):

        # --------- Button label updates --------
        if self.state == 'ready':
            self.ids.record_button.md_bg_color = self.color_orange
            self.ids.record_button.text = self.record_button_text

        if self.state == 'recording':
            self.ids.record_button.md_bg_color = self.color_green

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
        global emailFileMsg

        self.content = LoadDialog(emailfile=self.emailfile, cancel=self.cancel)
        print(f'=========== show_load path [{mp4Recorder.get_mp4_path()}] ==========')
        self.content.ids.filechooser.path = mp4Recorder.get_mp4_path()

        self._popup = Popup(title="Load file", content=self.content, size_hint=(0.9, 0.9))
        self._popup.open()

    # ---------------------------------------------
    #            emailfile
    # ---------------------------------------------
    def emailfile(self, path, selection, root):
        global emailFileMsg
        global mp4Recorder
                
        try:
            emailFileName = selection[0]
            if isfile(emailFileName):
                emailFileMsg = f'EmailFile [{emailFileName}] exists'
                print(f'-------------------- Root emailfile(): [{emailFileName}]')
                mp4Recorder.set_emailfile_filename(emailFileName)
                mp4Recorder.email(emailFileName)
                # timer() will clear emailFileName and isEmailFile
            else:            
                emailFileMsg = f'EmailFile error, file [{emailFileName}] does not exist'
                mp4Recorder.clear_emailfile_filename()
            self.dismiss_popup()
        except:
            pass

    # ---------------------------------------------
    #            cancel
    # ---------------------------------------------
    def cancel(self):
        global emailFileMsg
        global emilFileCancelMsg

        emailFileMsg = emilFileCancelMsg

        self.dismiss_popup()

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

###################################################################
# https://github.com/asyncgui/asynckivy/blob/main/examples/wait_for_a_thread_to_complete.py
#
# WIP: https://gist.github.com/el3/3c8d4e127d41e86ca3f2eae94c25c15f

if __name__ == '__main__':
    
    Mp4RecorderApp().run()
