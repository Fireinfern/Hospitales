from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtGui import *
from ortools.sat.python import cp_model
import itertools
import numpy as np
import inspect
import os
import folium
from folium import plugins
import pandas as pd
import io
import sys
from geopy import distance

def cargarHospitales(hosLoc, m_, nombres_):
  for i in range(len(hosLoc)):
    folium.Marker(
      location=hosLoc[i],
      popup=nombres_[i],
      icon=folium.Icon(color='red',icon='info-sign')
    ).add_to(m_)
  return m_

def CreateDistrictMarkers(loc_, m_, sev_, dist_, selectDist):
  for i in range(len(loc_)):
    if(dist_[i] == selectDist):
      folium.CircleMarker(location=loc_[i],border=False,fill_opacity=sev_[i]/2.5,radius=5,fill=True, color ='#FF0000').add_to(m_)
  return m_

def create_markers(df_lst, m_, sev_):
  for i in range(len(df_lst)):
    folium.CircleMarker(
        location=df_lst[i],
        radius=5,
        fill_opacity=sev_[i]/2.5,
        fill=True,
        color='#FF0000',
        border=False
    ).add_to(m_)
  return m_

def dist(p1, p2): 
    return np.round(distance.distance(p1,p2).km)

def main():
    df = pd.read_csv('casos_lima.csv', sep=';')
    hospitales = pd.read_csv('hospitales.csv', sep=';')
    Location_list= df.iloc[:,0:2].values.tolist()
    Severity_list = df.iloc[:,3].values.tolist()
    Distrito_list = df.iloc[:,2].values.tolist()
    hosLoc = hospitales.iloc[:,2:4].values.tolist()
    hosNombres = hospitales.iloc[:,0].values.tolist()
    
    ###Separacion de Datos
   
    ###
    m = folium.Map(location=[-12.0752, -77.05])
    data = io.BytesIO()
    m.save(data, close_file=False)

    def aplicarFiltros():
        actHospitals = []
        df = pd.read_csv('casos_lima.csv', sep=';')
        hospitales = pd.read_csv('hospitales.csv', sep=';')
        m = folium.Map(location=[-12.0752, -77.05])
        for i in range(len(chkHospList)):
            if(not(chkHospList[i].isChecked())):
                actHospitals += [i]
        hospitales = hospitales.drop(hospitales.index[actHospitals])
        hosLoc = hospitales.iloc[:,2:4].values.tolist()
        hosNombres = hospitales.iloc[:,0].values.tolist()
        m=cargarHospitales(hosLoc, m, hosNombres)
        DistritoSelect=cbxDistrito.currentText()
        if(DistritoSelect=='Jesus Maria'):
            m=CreateDistrictMarkers(Location_list,m,Severity_list,Distrito_list,"Jesus Maria")
            df = df.loc[df.Distrito=="Jesus Maria"]
        elif(DistritoSelect=='La Victoria'):
            m=CreateDistrictMarkers(Location_list,m,Severity_list,Distrito_list,"La Victoria")
            df = df.loc[df.Distrito=="La Victoria"]
        elif(DistritoSelect=='San Martin de Porres'):
            m=CreateDistrictMarkers(Location_list,m,Severity_list,Distrito_list,"San Martin de Porres")
            df = df.loc[df.Distrito=="San Martin de Porres"]
        elif(DistritoSelect=='Villa el Salvador'):
            m=CreateDistrictMarkers(Location_list,m,Severity_list,Distrito_list,"Villa el Salvador")
            df = df.loc[df.Distrito=="Villa el Salvador"]
        elif(DistritoSelect=='San Juan de Miraflores'):
            m=CreateDistrictMarkers(Location_list,m,Severity_list,Distrito_list,"San Juan de Miraflores")
            df = df.loc[df.Distrito=="San Juan de Miraflores"]
        else:
            m=create_markers(Location_list,m,Severity_list)
        data = io.BytesIO()
        m.save(data, close_file=False)
        webMap.setHtml(data.getvalue().decode())
        return df, hospitales

    def ResolveModel():
        df_, hospitales_ = aplicarFiltros()
        
        hosLoc = hospitales_.iloc[:,2:4].values.tolist()
        hosNombres = hospitales_.iloc[:,0].values.tolist()
        n_hospitales = len(hosLoc)
        n_pacientes = len(df_)
        if(rdbCamasUCI.isChecked()):
            n_camas_en_hospitales = [hospitales.iloc[i,5] for i in range(n_hospitales)]
        else:
            n_camas_en_hospitales = [hospitales.iloc[i,4] for i in range(n_hospitales)]
        #print(n_camas_en_hospitales)
        n_camas_total = sum(n_camas_en_hospitales)

        # Localizacion
        Location = df_.iloc[:,0:2]
        pacientes_loc = Location.values.tolist()
        LocationH = hospitales_.iloc[:,2:4]
        hospitales_loc = LocationH.values.tolist()
        # grado de contagio
        pacientes_contagio = df.iloc[:,3].values.tolist()
        ###

        max_dist=0
        for i in range(n_hospitales):
            for k in range(n_pacientes):
                d=dist(pacientes_loc[k],hospitales_loc[i])
                if max_dist<d:
                    max_dist=d

        ###Modelo CSP
        model = cp_model.CpModel()

        # variables y dominios
        x = {} #diccionarios en python
        for i in range(n_hospitales):
            for j in range(n_camas_en_hospitales[i]):
                for k in range(n_pacientes):
                    x[(i,j,k)] = model.NewBoolVar("x_" + str(i) + "_" + str(j) + "_" + str(k))

        coeff=[10,0.5]


        l = []
        for i in range(n_hospitales):
            for j in range(n_camas_en_hospitales[i]):
                for k in range(n_pacientes):
                    #l += [(1+coeff[0]*pacientes_contagio[k]-int(coeff[1]*dist(pacientes_loc[k],hospitales_loc[i])))*x[(i,j,k)]]
                    l += [(100+int(200*pacientes_contagio[k]/5)-int(100*dist(pacientes_loc[k],hospitales_loc[i])/max_dist))*x[(i,j,k)]]
        #model.Add(sum(l) > 0)
        model.Maximize(sum(l))

        #constraints
        for i in range(n_hospitales):
            for j in range(n_camas_en_hospitales[i]):
                model.Add(sum([x[(i,j,k)] for k in range(n_pacientes)]) <= 1)

        for k in range(n_pacientes):
            n_paciente_en_camas_hospitales = []
            for i in range(n_hospitales):
                n_paciente_en_camas_hospitales += [sum([x[(i,j,k)] for j in range(n_camas_en_hospitales[i])])]
            model.Add(sum(n_paciente_en_camas_hospitales) <= 1)
        ###

        solver = cp_model.CpSolver()
        status = solver.Solve(model)


        arcos=[]
        #print("N pacientes atendidos:",solver.ObjectiveValue())
        #print("Tiempo:",solver.WallTime())
        for i in range(n_hospitales):
            print("Hospital", i + 1,hospitales_loc[i])
            for j in range(n_camas_en_hospitales[i]):
                for k in range(n_pacientes):
                    if solver.Value(x[(i,j,k)]) == 1:
                        #print("\tPaciente", k + 1, "en cama", j + 1)
                        arcos.append((k,i))
        return pacientes_loc,hospitales_loc,arcos, hosLoc, hosNombres, df_
    
    def showMap():
        pacientes_loc,hospitales_loc,arcos, hosLoc, hosNombres, df_ = ResolveModel()
        Location_list= df_.iloc[:,0:2].values.tolist()
        Severity_list = df_.iloc[:,3].values.tolist()
        Distrito_list = df_.iloc[:,2].values.tolist()
        m = folium.Map(location=[-12.0752, -77.05])
        m=create_markers(Location_list,m, Severity_list)
        m=cargarHospitales(hosLoc, m, hosNombres)
        for i, j in arcos:
            linea = folium.PolyLine(locations=[[pacientes_loc[i][0], pacientes_loc[i][1]],
                                               [hospitales_loc[j][0],hospitales_loc[j][1]]], weight=1,color="blue")
            m.add_child(linea)
        data = io.BytesIO()
        m.save(data,close_file=False)
        webMap.setHtml(data.getvalue().decode())

    Distritos = ['Todos Los distritos','Jesus Maria','La Victoria', 'San Martin de Porres', 'Villa el Salvador', 'San Juan de Miraflores']
    app = QApplication([])
    app_icon = QIcon()
    app_icon.addFile('icon.png')
    MainWindow = QWidget()
    MainWindow.setWindowTitle('Distribucion de Pacientes COVID19')
    MainLayout = QHBoxLayout()
    OptionLayout = QVBoxLayout()
    lblDistrito = QLabel('Distrito:')
    cbxDistrito = QComboBox()
    cbxDistrito.addItems(Distritos)
    #mapa
    webMap = QWebEngineView()
    webMap.setHtml(data.getvalue().decode())
    #Seleccion de hospitales
    lblHospital= QLabel('Hospitales:')
    chkHospList = []
    for i in range(len(hosNombres)):
        chkHospList += [QCheckBox(hosNombres[i])]
    lblCantCamas = QLabel("Camas:")
    rdbCamasUCI = QRadioButton('Solo camas UCI')
    rdbCamasUCI.setChecked(True)
    btnAplicar = QPushButton('Aplicar')
    btnAplicar.clicked.connect(aplicarFiltros)
    btnResolver = QPushButton('Resolver')
    btnResolver.clicked.connect(showMap)

    OptionLayout.addWidget(lblDistrito)
    OptionLayout.addWidget(cbxDistrito)
    OptionLayout.addWidget(lblHospital)
    for i in range(len(hosNombres)):
        chkHospList[i].setChecked(True)
        OptionLayout.addWidget(chkHospList[i])
    OptionLayout.addWidget(lblCantCamas)
    OptionLayout.addWidget(rdbCamasUCI)
    OptionLayout.addWidget(btnAplicar)
    OptionLayout.addWidget(btnResolver)

    MainLayout.addLayout(OptionLayout)
    MainLayout.addWidget(webMap)
    MainWindow.setLayout(MainLayout)
    MainWindow.show()
    app.setWindowIcon(app_icon)
    app.exec_()

if __name__ == "__main__":
    main()