import cv2
import time
import os
import numpy as np
from source.postprocessing import PostProcessing
import matplotlib.pyplot as plt
from PySide2.QtCore import QTimer
from PySide2.QtGui import QPixmap, QImage

class Capture:
    def setup_camera(self):
        """
        Initialize camera.
        """
        self.capture = cv2.VideoCapture(self.camera_index)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.timer = QTimer()
        self.timer.timeout.connect(self.display_frame)
        self.timer.start(30)


    def display_frame(self):
        """
        Refresh frame from camera
        """
        try:
            self.ret, self.frame = self.capture.read()
            self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            # image = qimage2ndarray.array2qimage(self.frame)
            self.image = QImage(self.frame, self.frame.shape[1], self.frame.shape[0], 
                        self.frame.strides[0], QImage.Format_RGB888)
            self.ui.inputImg.setPixmap(QPixmap.fromImage(self.image))
        except:
            time.sleep(1)
            self.message_print(f'No se detectó cámara {self.camera_index}. Reintentando...')
            print(f'Camera was not detected on index {self.camera_index}')
            if self.camera_index < 5:
                self.camera_index += 1
                print(f'Retrying with index {self.camera_index}...')
            else:
                self.message_print("Error detectando cámara. Por favor revisar conexión.")
                self.timer.stop()
                pass

    
    def capture_image(self):
        """
        Captures a new image. Creates a new session with current timestamp if a session had
        not been created previously
        """
        self.current_secs = 1
        self.current_mins = 0
        self.timer_cron.start(1000)
        if (not self.sessionIsCreated):
            self.message_print("No se ha creado una sesion. Creando nueva...")
            time.sleep(1)
            self.create_session()
        
        if len(os.listdir(self.session_dir)) <= 1:
            image_number = len(os.listdir(self.session_dir))
        else:
            image_number = 5*len(os.listdir(self.session_dir)) - 5
        
        self.save_name = f't{image_number}.jpg'
        plt.imsave(os.path.join(self.session_dir, self.save_name), self.frame)
        self.ui.outputImg.setPixmap(QPixmap.fromImage(self.image))
        self.ui.imgName.setText(self.save_name[:-4])
        this_image = f"{self.defaultDirectory}/t{image_number}.jpg"
        self.ui.inputImgImport.setPixmap(this_image)
        self.find_images()
        
        if self.ui.autoScaleCheckBox.isChecked():
            # Read and set the temperature range:
            temp_scale = self.extract_scales_with_pytesseract(self.frame)
            self.ui.minSpinBox.setValue(temp_scale[0])
            self.ui.maxSpinBox.setValue(temp_scale[1])
    
    def tick(self):
        if self.current_secs < 10:
            self.ui.lcdNumber.display(f'{self.current_mins}:0{self.current_secs}')
        else:
            self.ui.lcdNumber.display(f'{self.current_mins}:{self.current_secs}')
        self.current_secs += 1
        if self.current_secs%60 == 0:
            self.current_mins += 1
            self.current_secs = 0
    
    def segment_capture(self):
        """
        Segment newly acquired capture with current loaded segmentation model
        """
        self.message_print("Segmentando imagen...")
        self.i2s.setModel(self.model)
        self.i2s.setPath(os.path.join(self.session_dir,self.save_name))
        self.i2s.loadModel()
        self.i2s.extract(cmap = self.input_cmap)
        threshold =  0.5   
        img = plt.imread(os.path.join(self.session_dir, self.save_name))/255
        Y = self.i2s.Y_pred
        Y = Y / Y.max()
        Y = np.where( Y >= threshold  , 1 , 0)
        post_processing = PostProcessing(self.ui.morphoSpinBox.value())
        u = post_processing.execute(Y[0])
        self.Y = u[0]     #Eventually required by temp_extract
        Y = np.copy(u)
        Y = cv2.resize(Y[0], (img.shape[1],img.shape[0]), interpolation = cv2.INTER_NEAREST) # Resize the prediction to have the same dimensions as the input 
        if self.ui.rainbowCheckBoxImport.isChecked():
            cmap = 'rainbow'
        else:
            cmap = 'gray'
        # plt.figure()
        # plt.plot(Y*img[:,:,0])
        # plt.savefig("outputs/output.jpg")
        plt.imsave("outputs/output.jpg" , Y*img[:,:,0] , cmap=cmap)
        self.ui.outputImg.setPixmap("outputs/output.jpg")
        self.isSegmented = True
        self.message_print("Imagen segmentada exitosamente")
        
    def feet_segment(self):
        """
        Segments a single feet image
        """
        self.message_print("Segmentando imagen...")
        self.i2s.setModel(self.model)
        self.i2s.setPath(self.opdir)
        self.i2s.extract(cmap = self.input_cmap)
        self.show_segmented_image()
        self.isSegmented = True
        self.message_print("Imagen segmentada exitosamente")