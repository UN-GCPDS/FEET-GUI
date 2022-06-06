from source.segment import ImageToSegment, SessionToSegment
from datetime import datetime
import os
import json

class RemoteOriginUnauthorizedException(Exception):
    """
    Exception raised when there is no authorization for actions on remote image repository
    """
    def __init__(self, URL):
        self.URL = URL
        self.message = f'Error in authorization with remote image repository {URL}.'
        super.__init__(self.message)

class Info:
    def populate_session_info(self):
        """
        Fill dictionary attribute with the parms given by the info tab
        """
        #Initial information obtained during session creation
        self.session_info['Nombre'] = self.ui.nameField.text()
        self.session_info['Edad'] = self.ui.ageField.text()
        self.session_info['Tipo_de_documento'] = self.ui.weightField.value()           #Spinbox
        self.session_info['Nro_de_documento'] = self.ui.weightField.text()
        self.session_info['Semanas_de_gestacion'] = self.ui.weeksField.value()         #Spinbox
        self.session_info['Peso'] = self.ui.weightField.value()                        #Spinbox
        self.session_info['Estatura'] = self.ui.heightField.value()                    #Spinbox
        if self.session_info['Estatura'] !=0 and self.session_info['Peso'] !=0:
            self.session_info['IMC'] = self.session_info['Peso']  / ( ( self.session_info['Estatura'] / 100 ) ** 2 ) #IMC=PESO/ESTATURA^2
        self.session_info['ASA'] = self.ui.ASAField.currentText()                      #Combobox
        self.session_info['Membranas'] = self.ui.membField.currentText()               #Combobox
        self.session_info['Dilatación'] = self.ui.dilatationField.value()              #Spinbox
        self.session_info['Paridad'] = self.ui.parityField.currentText()               #Combobox

        #Calculated additional information
        self.session_info['Temperaturas_medias'] = self.meanTemperatures
        self.session_info['Escalas_de_temperatura'] = self.scale_range
        self.session_info['Temperaturas_de_dermatomas'] = self.dermatomes_temps.tolist()

    

    def wipe_outputs(self, hard=False):
        self.message_print("Limpiando sesión...")
        self.imgs = []
        self.subj = []
        self.inputExists = False
        self.defaultDirectoryExists = False
        self.isSegmented = False
        self.files = None
        self.temperaturesWereAcquired = False
        self.s2s = SessionToSegment()
        self.i2s = ImageToSegment()
        self.s2s.setModel(self.model)
        self.i2s.setModel(self.model)
        self.s2s.loadModel()
        self.i2s.loadModel()
        self.sessionIsCreated = False
        self.ui.outputImgImport.setPixmap("")
        self.ui.inputImgImport.setPixmap("")
        self.ui.outputImg.setPixmap("")
        self.ui.temperatureLabelImport.setText("")

        if hard:
            self.ui.nameField.setText("")
            self.ui.ageField.setText("")
            self.ui.weightField.setValue(0)                 
            self.ui.weightField.setValue(0)
            self.ui.weeksField.setValue(0)                  
            self.ui.weightField.setValue(0)                 
            self.ui.heightField.setValue(0)                 
            self.ui.ASAField.setCurrentIndex(0)             
            self.ui.membField.setCurrentIndex(0)            
            self.ui.dilatationField.setValue(0)             
            self.ui.parityField.setCurrentIndex(0)          


    def create_session(self):
        """
        Creates a new session, including a directory in ./outputs/<session_dir> with given input parameters
        from GUI
        The session is named as the current timestamp if current session_dir is null
        """
        self.name = self.ui.nameField.text()
        formatted_today = datetime.today().strftime("%Y-%m-%d_%H:%M")            
        self.dir_name = f"{self.name.replace(' ','_')}{formatted_today}"
        try:
            self.wipe_outputs()
            self.session_dir = os.path.join('outputs',self.dir_name)
            os.mkdir(self.session_dir)
            self.sessionIsCreated = True
            self.message_print("Sesión " + self.session_dir + " creada exitosamente." )
            self.defaultDirectoryExists = True
            self.defaultDirectory = os.path.abspath(self.session_dir)
            self.inputExists = True
            self.sessionIsSegmented = False
            self.input_type = 2 #Video input capture
        except Exception as ex:
            self.message_print("Fallo al crear la sesión. Lea el manual de ayuda para encontrar solución, o reporte bugs al " + self.bugsURL)
            print(ex)
        
    def sync_local_info_to_drive(self):
        """
        Syncs info from the output directory to the configured sync path
        """
        self.message_print("Sincronizando información al repositorio remoto...")
        try:
            status = os.system("rclone copy outputs drive:")
            self.message_print("Sincronizando información al repositorio remoto...")
            if self.rcloneIsConfigured:
                if status == 0:
                    self.message_print("Se ha sincronizado exitosamente la información")
                    return
                raise Exception("Error sincronizando imagenes al repositorio remoto")
            raise RemoteOriginUnauthorizedException(self.driveURL)
        except RemoteOriginUnauthorizedException as ue:
            self.message_print("Error de autorización durante la sincronización. Dirígase a Ayuda > Acerca de para más información.")
            print(ue)
        except Exception as e:
            self.message_print("Error al sincronizar la información al repositorio. Verifique que ha seguido los pasos de instalación y configuración de rclone. Para más información, dirígase a Ayuda > Acerca de.")
            print(e)

    def repo_config_dialog(self):
        """
        Shows a dialog window for first time configuring the remote repository sync for the current device
        """
        raise NotImplementedError()
        
    def display_how_to_use(self):
        """
        Displays user manual on system's default pdf viewer
        """
        os.system("xdg-open README.html")
        
    def export_report(self):
        """
        Generates a json document with session information
        """
        with open(f"{self.defaultDirectory}/report.json", "w") as outfile:
            json.dump(self.session_info, outfile)