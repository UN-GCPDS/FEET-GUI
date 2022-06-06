import time
import os
from PySide2.QtWidgets import QFileDialog 
from PySide2.QtCore import QDir

class RemotePullException(Exception):
    def __init__(self, repoURL):
        self.message = "Error pulling new changes into local DB from origin: " + str(repoURL)
        super.__init__(self.message)

class Config:
    def toggle_input_colormap(self):
        self.input_cmap = self.accepted_cmaps[self.ui.inputColormapComboBox.currentIndex()]
        self.message_print(f"Se ha cambiado exitosamente el colormap de entrada a {self.input_cmap}")

    def set_default_input_cmap(self):
        self.accepted_cmaps = ['Gris', 'Hierro', 'Arcoiris', 'Lava']
        self.input_cmap = self.accepted_cmaps[0]
        self.ui.inputColormapComboBox.addItems(self.accepted_cmaps)
        
    def set_default_config_settings(self, model_dir, session_dir):
        """
        Sets default config settings
        """
        self.config = {'models_directory': model_dir,
                'session_directory': session_dir }

    def update_user_configuration(self):
        """
        Updates basic configuration
        """
        self.modelsPath = self.config['models_directory']
        self.defaultDirectory = self.config['session_directory']
        
    def update_software(self):
        """
        Updates software from remote origin repository
        """
        try:
            self.message_print(f"Actualizando software desde {self.repoUrl}...")
            time.sleep(2)
            exit_value = os.system("git pull")
            if exit_value == 0:
                self.message_print("Se ha actualizado exitosamente la interfaz. Se sugiere reiniciar interfaz")
                return
            self.message_print("Error al actualizar.")
            raise RemotePullException(self.repoUrl)
        except:
            self.message_print("Error al actualizar.")
            raise RemotePullException(self.repoUrl)
        
    def get_models_path(self):
        """
        Display a file manager dialog for selecting model list root directory
        """
        self.modelDialog=QFileDialog(self)
        self.modelDialog.setDirectory(QDir.currentPath())        
        self.modelDialog.setFileMode(QFileDialog.FileMode.Directory)
        self.modelsPath = self.modelDialog.getExistingDirectory()
        if self.modelsPath:
            self.modelsPathExists = True
            self.modelList = []
            for root, dirs, files in os.walk(self.modelsPath):
                for file in files:
                    self.modelList.append(os.path.join(root,file))
            self.modelQuantity = len(self.modelList)
            self.modelIndex = 0
            self.models = files
            self.ui.modelComboBox.addItems(self.models)
        
    def toggle_model(self):
        """
        Change model loaded if user changes the model modelComboBox
        """
        self.modelIndex = self.ui.modelComboBox.currentIndex()
        self.message_print("Cargando modelo: " + self.models[self.modelIndex]
                        +" Esto puede tomar unos momentos...")
        try:
            self.model = self.modelList[self.modelIndex]
            self.s2s.setModel(self.model)
            self.i2s.setModel(self.model)
            self.s2s.loadModel()
            self.i2s.loadModel()
            self.ui.loadedModelLabel.setText(self.model)
            self.message_print("Modelo " + self.models[self.modelIndex] + " cargado exitosamente")
        except:
            self.message_print("Error al cargar el modelo "+ self.models[self.modelIndex])