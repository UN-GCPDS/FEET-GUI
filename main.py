# GCPDS - Universidad Nacional de Colombia
# Proyecto caracterización termográfica de extremidades inferiores durante aplicación de anestesia epidural
# Mayo de 2021
# Disponible en https//:github.com/blotero/FEET-GUI

import os

from pathlib import Path
import sys
import matplotlib.pyplot as plt

from PySide2.QtWidgets import QApplication 
from PySide2.QtCore import QFile, QObject, SIGNAL, QDir, QTimer
from PySide2.QtUiTools import QUiLoader 
from source.segment import ImageToSegment, SessionToSegment


from PySide2.QtWidgets import QFileSystemModel
from PySide2.QtGui import QTextCursor
import tflite_runtime.interpreter as tflite

from source.captura import Capture
from source.analisis import Analisis
from source.info import Info
from source.config import Config
from source.display import Display


class NotImplementedError(Exception):
    """
    Error raised from methods that have not been implemented
    """
    def __init__(self):
        self.message = "This feature has not been implemented" 
        super.__init__(self.message)

    

class Window(Capture, Analisis, Info, Config, Display):
    def __init__(self):
        super(Window, self).__init__()
        self.load_UI()        
        self.imgs = []
        self.subj = []
        self.make_connect()
        self.init_logs()
        self.inputExists = False
        self.defaultDirectoryExists = False
        self.isSegmented = False
        self.files = None
        self.temperaturesWereAcquired = False
        self.scaleModeAuto = True
        self.modelsPathExists = True   #As soon as the model is present in the expected path
        self.model = 'default_model.tflite'
        self.fullScreen = True
        #Loading segmentation models
        self.s2s = SessionToSegment()
        self.i2s = ImageToSegment()
        self.s2s.setModel(self.model)
        self.i2s.setModel(self.model)
        self.s2s.loadModel()
        self.i2s.loadModel()
        self.ui.loadedModelLabel.setText(self.model)
        self.camera_index = 0
        self.setup_camera()
        self.sessionIsCreated = False
        self.driveURL = None
        self.rcloneIsConfigured = False
        self.repoUrl = 'https://github.com/blotero/FEET-GUI.git' 
        self.digits_model = tflite.Interpreter(model_path = './digits_recognition.tflite')
        self.digits_model.allocate_tensors()
        self.set_default_input_cmap()
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.currentPath())
        self.ui.treeView.setModel(self.file_system_model)
        plt.style.use('bmh')
        self.session_info = {}
        self.ui.progressBar.setVisible(False)
        self.timer_cron = QTimer()
        self.timer_cron.timeout.connect(self.tick)
        
    
    def load_UI(self):
        """
        Load xml file with visual objects for the interface
        """
        loader = QUiLoader()        
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file)
        self.ui.showFullScreen()
        ui_file.close()
 

    def make_connect(self):
        """
        Makes all connections between singleton methods and objects in UI xml
        """
        QObject.connect(self.ui.actionCargar_imagen, SIGNAL ('triggered()'), self.open_image)
        QObject.connect(self.ui.actionCargar_carpeta , SIGNAL ('triggered()'), self.open_folder)
        QObject.connect(self.ui.actionCargar_modelos , SIGNAL ('triggered()'), self.get_models_path)
        QObject.connect(self.ui.actionPantalla_completa , SIGNAL ('triggered()'), self.toggle_fullscreen)
        QObject.connect(self.ui.actionSalir , SIGNAL ('triggered()'), self.exit_)
        QObject.connect(self.ui.actionC_mo_usar , SIGNAL ('triggered()'), self.display_how_to_use)
        QObject.connect(self.ui.actionUpdate , SIGNAL ('triggered()'), self.update_software)
        QObject.connect(self.ui.actionRepoSync , SIGNAL ('triggered()'), self.sync_local_info_to_drive)
        QObject.connect(self.ui.actionRepoConfig , SIGNAL ('triggered()'), self.repo_config_dialog)
        QObject.connect(self.ui.segButtonImport, SIGNAL ('clicked()'), self.segment)
        QObject.connect(self.ui.tempButtonImport, SIGNAL ('clicked()'), self.temp_extract)
        QObject.connect(self.ui.captureButton, SIGNAL ('clicked()'), self.capture_image)
        QObject.connect(self.ui.nextImageButton , SIGNAL ('clicked()'), self.next_image)
        QObject.connect(self.ui.previousImageButton , SIGNAL ('clicked()'), self.previous_image)
        #QObject.connect(self.ui.reportButton , SIGNAL ('clicked()'), self.export_report)
        QObject.connect(self.ui.reportButton , SIGNAL ('clicked()'), self.generate_full_session_plot)
        QObject.connect(self.ui.loadModelButton , SIGNAL ('clicked()'), self.toggle_model)
        QObject.connect(self.ui.createSession, SIGNAL ('clicked()'), self.create_session)
        QObject.connect(self.ui.segButton, SIGNAL ('clicked()'), self.segment_capture)
        #Comboboxes:
        self.ui.inputColormapComboBox.currentIndexChanged['QString'].connect(self.toggle_input_colormap)

    def init_logs(self):
        log_path = "outputs/logs.html"
        open(log_path, 'w').close()
        out_file = open(log_path , "a")
        final_msg = f'<meta charset="UTF-8">\n'
        out_file.write(final_msg)
        out_file.close()

    def message_print(self, message):
        """
        Prints on interface console
        """
        log_path = "outputs/logs.html"
        out_file = open(log_path , "a")
        final_msg = f"\n <br> >>> </br>  {message}\n"
        out_file.write(final_msg)
        out_file.close()
        self.ui.textBrowser.setSource(log_path)
        self.ui.textBrowser.reload()
        self.ui.textBrowser.moveCursor(QTextCursor.End)

    def get_times(self):
        """
        Converts standarized names of file list into a list of 
        integers with time capture in minutes from the acquired self.fileList 
        from self.find_images
        """
        if (type(self.fileList)==str):
            self.timeList =  int(self.fileList).rsplit(".")[0][1:]
        elif type(self.fileList)==list:    
            out_list = []
            for i in range(len(self.fileList)):
                out_list.append(int(self.files[i].rsplit(".")[0][1:]))
            self.timeList =  out_list
        else:
            return None

    def toggle_fullscreen(self):
        """
        Toggles fullscreen state
        """
        if self.fullScreen:
            self.ui.showNormal()
            self.fullScreen = False
        else:
            self.ui.showFullScreen()
            self.fullScreen = True

    def exit_(self):
        sys.exit(app.exec_())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.ui.show()
    #window.ui.show()
    sys.exit(app.exec_())
