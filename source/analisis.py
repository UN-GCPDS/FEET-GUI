import os
import re
import cv2
import numpy as np
import pytesseract
from source.temperatures import mean_temperature, dermatomes_temperatures
import time
 
class Analisis:
    def predict_number(self,image):
        """
        Predicts digit value from a certain region image
        """

        image_2 = cv2.resize(image, (28, 28), interpolation = cv2.INTER_NEAREST)
        
        image_2 = cv2.cvtColor(np.uint8(image_2), cv2.COLOR_BGR2GRAY)
        
        image_2 = np.expand_dims(image_2, -1)

        image_2 = np.expand_dims(image_2, 0)
        input_details = self.digits_model.get_input_details()
        output_details = self.digits_model.get_output_details()

        #input_shape = input_details[0]['shape']
        input_data = np.float32(image_2)

        self.digits_model.set_tensor(input_details[0]['index'], input_data)

        self.digits_model.invoke()  # predict

        output_data = self.digits_model.get_tensor(output_details[0]['index'])

        return np.argmax(output_data)  
        
    def predict_number_with_pytesseract(self, img):
        """
        Obtain number from section of an image
        """
        uint8img = img.astype("uint8")
        #print(np.unique(uint8img))
        #print(uint8img.shape)
        thresh = cv2.threshold(uint8img , 100, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]
        #plt.figure()
        # plt.imshow(thresh)
        text = pytesseract.image_to_string(thresh,   config = '--psm 7')
        #Text cleaning and replacement...
        clean_text = text.replace('\n','').replace('-]', '4').replace(']', '1').replace(' ', '').replace(',', '.').replace('%', '7').replace('€','9').replace('[','').replace('&', '5').replace('-','3')
        # plt.title(clean_text)
        # plt.show()
        try:
            num = float(clean_text)
            if num>=100:
                num/=10
        except:
            print(f"Could not convert string {clean_text} into number")
            self.message_print(f"No se ha podido detectar escalas automáticamente de: Texto base: {text}, Texto limpio: {clean_text}. Dejando rango por defecto: [25, 45]")
            return -100
        return num


    def extract_scales_with_pytesseract(self,x):
        """
        Extracts float lower and upper scales from a thermal image with pytesseract
        """
        lower_seg = x[445: 467, 575: 625,0]
        upper_seg = x[14: 34, 576: 624,0]
        lower_prediction = self.predict_number_with_pytesseract(lower_seg)
        upper_prediction = self.predict_number_with_pytesseract(upper_seg)
        
        if lower_prediction == -100:
            lower_prediction = 25
        if upper_prediction == -100:
            upper_prediction = 45
        return lower_prediction, upper_prediction

     
    def extract_scales_2(self,x):
        """
        Exctract scales with easyocr (deprecated)
        """
        x = np.uint8(x[:,560:,:])
        #print(x) 
        result = self.reader.readtext(x,detail=0)
        #print(result)    
        try:
            result = [float(number) for number in result]
        except:
            self.message_print("No se ha podido detectar escalas automáticamente. Dejando rango por defecto: [25, 45]")
            return 25, 45
        
        lower = min(result)
        upper = max(result)
        self.message_print(f"Escala leida: {lower, upper}. Por favor verifique que sea la correcta y corríjala en caso de que no lo sea.")
        
        return lower, upper
     
     
    def extract_scales(self, x):
        """
        Extracts float lower and upper scales from a thermal image
        """
        lower_digit_1 = self.predict_number(x[445: 467, 575: 591])
        lower_digit_2 = self.predict_number(x[445: 467, 589: 605])
        lower_digit_3 = self.predict_number(x[445: 467, 609: 625])
        
        upper_digit_1 = self.predict_number(x[14: 34, 576: 590])
        upper_digit_2 = self.predict_number(x[14: 34, 590: 604])
        upper_digit_3 = self.predict_number(x[14: 34, 610: 624])

        lower_bound = lower_digit_1*10 + lower_digit_2 + lower_digit_3*0.1
        upper_bound = upper_digit_1*10 + upper_digit_2 + upper_digit_3*0.1

        return lower_bound, upper_bound

    def extract_multiple_scales(self, X):
        """
        Extracts scales from a whole imported session
        """
        scales = []
        for i in range(X.shape[0]):
            scales.append(self.extract_scales_with_pytesseract(X[i]))
            
        return scales
        
    def next_image(self):
        """
        Displays next image from self.fileList
        """
        if self.imageIndex < len(self.fileList)-1:
            self.imageIndex += 1
            self.ui.inputImgImport.setPixmap(self.fileList[self.imageIndex])
            self.opdir = self.fileList[self.imageIndex]
            self.ui.inputLabel.setText(self.files[self.imageIndex])

            if self.sessionIsSegmented:
                #Sentences to display next output image if session was already
                #segmented
                self.show_output_image_from_session()
                if self.temperaturesWereAcquired:
                    self.message_print(f"La temperatura media de pies es:  {np.round(self.meanTemperatures[self.imageIndex], 2)} para el tiempo:{self.files[self.imageIndex].replace('.jpg','')}")
                    rounded_temp = np.round(self.meanTemperatures[self.imageIndex], 2)
                    self.ui.temperatureLabelImport.setText(f'{rounded_temp} °C')
                    self.ui.minSpinBoxImport.setValue(self.scale_range[self.imageIndex][0])
                    self.ui.maxSpinBoxImport.setValue(self.scale_range[self.imageIndex][1])
                
    def previous_image(self):
        """
        Displays previous image from self.fileList
        """
        if self.imageIndex >= 1:
            self.imageIndex -= 1
            self.ui.inputImgImport.setPixmap(self.fileList[self.imageIndex])
            self.opdir = self.fileList[self.imageIndex]
            self.ui.inputLabel.setText(self.files[self.imageIndex])

            if self.sessionIsSegmented:
                #Sentences to display next output image if session was already
                #segmented
                self.show_output_image_from_session()
                if self.temperaturesWereAcquired:
                    self.message_print(f"La temperatura media de pies es:  {np.round(self.meanTemperatures[self.imageIndex], 2)} para el tiempo:{self.files[self.imageIndex].replace('.jpg','')}")
                    rounded_temp = np.round(self.meanTemperatures[self.imageIndex], 2)
                    self.ui.temperatureLabelImport.setText(f'{rounded_temp} °C')
                    self.ui.minSpinBoxImport.setValue(self.scale_range[self.imageIndex][0])
                    self.ui.maxSpinBoxImport.setValue(self.scale_range[self.imageIndex][1])
        
    def find_images(self):
        """
        Finds image from the path established in self.defaultDirectory obtained 
        from the method self.open_folder
        """
        self.fileList = []  #Absolute paths
        self.files = []     #Relative paths
        self.outfiles=[]    #Relative path to output files
        for root, dirs, files in os.walk(self.defaultDirectory):
            for file in files:
                if (file.endswith(".jpg")):
                    self.fileList.append(os.path.join(root,file))
                    self.files.append(file) 
                    self.outfiles.append("outputs/" + file) #Creating future output file names
        self.imageQuantity = len(self.fileList)
        self.imageIndex = 0
        self.sort_files()
        self.ui.inputLabel.setText(self.files[self.imageIndex])

    def sort_files(self):
        """
        Sort file list to an alphanumeric reasonable sense
        """         
        convert = lambda text: int(text) if text.isdigit() else text 
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
        self.fileList =  sorted(self.fileList, key = alphanum_key)
        self.files =  sorted(self.files, key = alphanum_key)
        
    def temp_extract(self):
        """
        Extract temperatures from a segmented image or a whole session
        """
        self.ui.progressBar.setVisible(True)
        self.ui.progressBar.setValue(0)
        self.message_print("Obteniendo temperaturas...")
        if (self.inputExists and (self.isSegmented or self.sessionIsSegmented)):
            self.message_print("Obteniendo temperaturas de la sesión...")
            self.ui.progressBar.setFormat("Extrayendo temperaturas... %p%")

            if self.ui.autoScaleCheckBoxImport.isChecked and self.input_type>=1:
                #Get automatic scales
                self.scale_range = self.extract_multiple_scales(self.s2s.img_array)
                
            elif not self.ui.autoScaleCheckBoxImport.isChecked():
                self.scale_range = [self.ui.minSpinBoxImport.value() , self.ui.maxSpinBoxImport.value()] 

            if self.input_type>=1:   #If segmentation was for full session
                self.meanTemperatures = []   #Whole feet mean temperature for all images in session
                segmented_temps = []
                original_temps = []
                dermatomes_temps = []
                dermatomes_masks = []
                if self.ui.autoScaleCheckBoxImport.isChecked():
                    for i in range(len(self.outfiles)):
                        mean_out, temp, original_temp = mean_temperature(self.s2s.Xarray[i,:,:,0] , self.Y[i][:,:,0] , self.scale_range[i], plot = False)
                        derm_temps, derm_mask = dermatomes_temperatures(original_temp, self.Y[i])
                        self.meanTemperatures.append(mean_out)
                        segmented_temps.append(temp)
                        original_temps.append(original_temp)
                        dermatomes_temps.append(derm_temps)
                        dermatomes_masks.append(derm_mask)
                        self.ui.progressBar.setValue((100*i+1)/len(self.outfiles))
                    self.dermatomes_temps = np.array(dermatomes_temps)
                    self.dermatomes_masks = np.array(dermatomes_masks)
                    self.segmented_temps = np.array(segmented_temps)
                    self.original_temps = np.array(original_temps)

                else:
                    for i in range(len(self.outfiles)):
                        mean_out, temp, original_temp = mean_temperature(self.s2s.Xarray[i,:,:,0] , self.Y[i][:,:,0] , self.scale_range, plot = False)
                        derm_temps, derm_mask = dermatomes_temperatures(original_temp, self.Y[i])
                        self.meanTemperatures.append(mean_out)
                        segmented_temps.append(temp)
                        original_temps.append(original_temp)
                        dermatomes_temps.append(derm_temps)
                        dermatomes_masks.append(derm_mask)
                        self.ui.progressBar.setValue((100*i+1)/len(self.outfiles))
                    self.dermatomes_temps = np.array(dermatomes_temps)
                    self.dermatomes_masks = np.array(dermatomes_masks)
                    self.segmented_temps = np.array(segmented_temps)
                    self.original_temps = np.array(original_temps)


                self.message_print("La temperatura media es: " + str(self.meanTemperatures[self.imageIndex]))
                self.message_print(f"La escala leida es: {self.scale_range[self.imageIndex]}")
                rounded_temp = np.round(self.meanTemperatures[self.imageIndex], 3)
                self.ui.temperatureLabelImport.setText(f'{rounded_temp} °C')
                self.ui.minSpinBoxImport.setValue(self.scale_range[self.imageIndex][0])
                self.ui.maxSpinBoxImport.setValue(self.scale_range[self.imageIndex][1])
                self.temperaturesWereAcquired = True
            else:      #If segmentation was for single image
                if self.ui.autoScaleCheckBoxImport.isChecked():
                    self.scale_range = self.extract_scales_with_pytesseract(self.i2s.img)
                else:
                    self.scale_range = [self.ui.minSpinBoxImport.value() , self.ui.maxSpinBoxImport.value()]
                time.sleep(1.5)
                mean, _ = mean_temperature(self.i2s.Xarray[:,:,0] , self.Y[:,:,0] , self.scale_range, plot = False)
                self.message_print("La temperatura media es: " + str(mean))
                rounded_temp = np.round(mean, 3)
                self.ui.temperatureLabelImport.setText(f'{rounded_temp} °C')

            if (self.ui.plotCheckBoxImport.isChecked() and self.input_type>=1):  #If user asked for plot
                #self.message_print("Se generara plot de temperatura...")
                self.get_times()
                # self.temp_plot()

        elif self.inputExists:
            #If input exists but session has not been segmented
            self.message_print("No se ha segmentado previamente la sesión. Segmentando... ")
            time.sleep(1)
            self.session_segment()
            self.temp_extract()
        elif self.ui.tabWidget.currentIndex() == 0:
            #Live video tab
            self.message_print("Obteniendo temperaturas para la última captura...")
            time.sleep(1)
            if not self.sessionIsCreated:
                self.message_print("No se ha creado una sesión de entrada. Presione capturar para crear una sesión por defecto o cree una con los parámetros deseados")
                return
            if len(os.listdir(self.session_dir)) < 1:
                self.message_print("No se ha hecho ninguna captura.")
                return
            #HERE COMES TO LOGIC FOR OBTAINING FULL PLOT FOR LIVE VIDEO

        else:
            self.message_print("No se han seleccionado imagenes de entrada")

        self.ui.progressBar.setVisible(False)
        self.ui.progressBar.setFormat("%p%")
        
    def session_segment(self):
        """
        Segments a whole feet session
        """
        self.ui.progressBar.setVisible(True)
        self.ui.progressBar.setFormat("Segmentando..%p%")
        self.ui.progressBar.setValue(0)
        time.sleep(0.5)
        self.sessionIsSegmented = False
        self.s2s.setModel(self.model)
        self.s2s.setPath(self.defaultDirectory)
        self.s2s.whole_extract(self.fileList, cmap = self.input_cmap, progressBar = self.ui.progressBar)
        self.produce_segmented_session_output()
        self.show_output_image_from_session()
        self.message_print("Se ha segmentado exitosamente la sesion con "+ self.i2s.model)
        self.sessionIsSegmented = True
        self.ui.progressBar.setValue(100)
        # time.sleep(0.5)
        self.ui.progressBar.setVisible(False)
        self.ui.progressBar.setFormat("%p%")

    def segment(self):
        """
        Makes segmentation action depending on the current state (single image or whole session)
        """
        if self.input_type >= 1:
            #Session
            if self.defaultDirectoryExists and self.i2s.model!=None and self.s2s.model!=None:
                self.message_print("Segmentando toda la sesión...")
                self.session_segment()
            else:
                self.message_print("Error. Por favor verifique que se ha cargado el modelo y la sesión de entrada.")
        elif self.input_type == 0:
            #Single image
            if self.inputExists and self.modelsPathExists and self.model!=None:
                print('YOLO')
                self.feet_segment()
            else:
                self.message_print("No se ha seleccionado imagen de entrada")