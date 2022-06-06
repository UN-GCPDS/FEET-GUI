import matplotlib.pyplot as plt
import numpy as np
import cv2
import os
from scipy.interpolate import make_interp_spline 
from PySide2.QtWidgets import QFileDialog
from PySide2.QtCore import QDir
from source.report import plot_report
from source.postprocessing import PostProcessing
from PySide2.QtWidgets import *

class Display:
    def open_image(self):
        """
        Displays a dialog for loading a single image
        """
        self.fileDialog=QFileDialog()
        if self.defaultDirectoryExists:
            self.fileDialog.setDirectory(self.defaultDirectory)
        else:
            self.fileDialog.setDirectory(QDir.currentPath())        
        #filters =  ["*.png", "*.xpm", "*.jpg"]
        self.fileDialog.setNameFilters("Images (*.png *.jpg)")
        self.fileDialog.selectNameFilter("Images (*.png *.jpg)")
        #self.fileDialog.setFilter(self.fileDialog.selectedNameFilter())
        self.opdir = self.fileDialog.getOpenFileName()[0]
        self.imagesDir = os.path.dirname(self.opdir) 
        if self.opdir:
            self.wipe_outputs(hard=True)
            self.input_type = 0
            self.inputExists = True
            self.ui.inputImgImport.setPixmap(self.opdir)
            self.message_print(f"Se ha importado exitosamente la imagen {self.opdir} ")
            self.ui.tabWidget.setProperty('currentIndex', 1)

    def open_folder(self):
        """
        Displays a dialog for loading a whole session
        """
        self.folderDialog=QFileDialog()
        self.folderDialog.setDirectory(QDir.currentPath())        
        self.folderDialog.setFileMode(QFileDialog.FileMode.Directory)
        self.defaultDirectory = self.folderDialog.getExistingDirectory()
        self.imagesDir = self.defaultDirectory
        if self.defaultDirectory:
            self.wipe_outputs(hard=True)
            self.input_type = 1
            self.defaultDirectoryExists = True
            first_image = str(self.defaultDirectory + "/t0.jpg")
            self.ui.inputImgImport.setPixmap(first_image)
            self.opdir = first_image
            self.inputExists = True
            self.find_images()
            self.sessionIsSegmented = False
            self.ui.tabWidget.setProperty('currentIndex', 1)
            self.message_print(f"Se ha importado exitosamente la sesión {self.defaultDirectory} ")
            #self.file_system_model.setRootPath(QDir(self.defaultDirectory))
            #self.ui.treeView.setModel(self.file_system_model)
            
    def show_segmented_image(self):
        """
        Shows segmented image
        """
        #Applies segmented zone to input image, showing only feet
        threshold =  0.5
        img = plt.imread(self.opdir)/255
        Y = self.i2s.Y_pred
        Y = Y / Y.max()
        Y = np.where( Y >= threshold  , 1 , 0)
        self.Y = posprocessing(Y[0])[0]     #Eventually required by temp_extract
        Y = posprocessing(Y[0])
        Y = cv2.resize(Y[0], (img.shape[1],img.shape[0]), interpolation = cv2.INTER_NEAREST) # Resize the prediction to have the same dimensions as the input 
        if self.ui.rainbowCheckBoxImport.isChecked():
            cmap = 'rainbow'
        else:
            cmap = 'gray'
        plt.figure()
        plt.plot(Y*img[:,:,0])
        plt.savefig("outputs/output.jpg")
        plt.imsave("outputs/output.jpg" , Y*img[:,:,0] , cmap=cmap)
        self.ui.outputImgImport.setPixmap("outputs/output.jpg")
    
    def temp_plot(self):
        """
        Plots from acquired temperature samples from a session
        """
        plt.figure()
        x = np.linspace(min(self.timeList), max(self.timeList), 200)
        spl = make_interp_spline(self.timeList, self.meanTemperatures, k=3)
        y = spl(x) 
        plt.plot(x , y, '-.', color='salmon')
        plt.plot(self.timeList , self.meanTemperatures , '-o', color='slategrey')
        plt.title("Temperatura media de pies")
        plt.xlabel("Tiempo (min)")
        plt.ylabel("Temperatura (°C)")
        plt.grid()
        plt.show()
        self.message_print("Plot de temperatura generado exitosamente")
        #Produce plot 


    def generate_full_session_plot(self):
        if not self.temperaturesWereAcquired :
            self.message_print("No se han extraido las temperaturas, extrayendo...")
            self.temp_extract()
            self.generate_full_session_plot()
        else:
            exit_value = plot_report(img_temps = self.original_temps, segmented_temps = self.segmented_temps, mean_temps = self.meanTemperatures, times = self.timeList, 
                        path = os.path.join(self.defaultDirectory,'report'), dermatomes_temps = self.dermatomes_temps, dermatomes_masks = self.dermatomes_masks)
            if exit_value == 0:
                #Generación de información extra para la sesión
                self.message_print("Se ha generado exitosamente el plot completo de sesión")
            else:
                self.message_print("Advertencia, se ha encontrado un valor no válido (nan) en los dígitos de escala de temperatura. Verifique que la imagen es del formato y referencia de cámara correctos")
            self.populate_session_info()
            self.export_report()
    
    def produce_segmented_session_output(self):
        """
        Produce output images from a whole session and 
        Recursively applies show_segmented_image to whole session
        """
        self.Y=[]
        post_processing = PostProcessing(self.ui.morphoSpinBox.value())
        for i in range(len(self.outfiles)):
            threshold =  0.5
            img = plt.imread(self.fileList[i])/255
            Y = self.s2s.Y_pred[i]
            Y = Y / Y.max()
            Y = np.where( Y >= threshold  , 1 , 0)
            Y = post_processing.execute(Y[0])
            
            self.Y.append(Y)    #Eventually required by temp_extract
            
            #print(f"Dimensiones de la salida: {Y.shape}")
            Y = cv2.resize(Y, (img.shape[1],img.shape[0]), interpolation = cv2.INTER_NEAREST) # Resize the prediction to have the same dimensions as the input 
            
            if self.ui.rainbowCheckBox.isChecked():
                cmap = 'rainbow'
            else:
                cmap = 'gray'
            # plt.figure()
            # plt.imshow(Y*img[:,:,0])
            # plt.axis('off')
            # plt.savefig(self.outfiles[i])
            plt.imsave(self.outfiles[i], Y*img[:,:,0] , cmap=cmap)


    def show_output_image_from_session(self):
        """
        Display segmented image from current one selected from the index 
        established by self.previous_image or self.next_image methods
        """
        self.ui.outputImgImport.setPixmap(self.outfiles[self.imageIndex])