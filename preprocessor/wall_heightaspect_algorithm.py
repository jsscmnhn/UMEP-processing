# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ProcessingUMEP
                                 A QGIS plugin
 UMEP for processing toolbox
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-04-02
        copyright            : (C) 2020 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Fredrik Lindberg'
__date__ = '2020-04-02'
__copyright__ = '(C) 2020 by Fredrik Lindberg'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsRasterFileWriter,
                       QgsMessageLog,
                       QgsProcessingParameterBoolean,
                       Qgis)

from qgis.PyQt.QtWidgets import QAction, QFileDialog, QMessageBox
from osgeo import gdal
from osgeo.gdalconst import *
import numpy as np
import os
from ..functions import wallalgorithms as wa
from qgis.PyQt.QtGui import QIcon
import inspect
from pathlib import Path
from ..util.misc import saverasternd


# def saverasternd(gdal_data, filename, raster):
#     rows = gdal_data.RasterYSize
#     cols = gdal_data.RasterXSize

#     outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
#     outBand = outDs.GetRasterBand(1)

#     # write the data
#     outBand.WriteArray(raster, 0, 0)
#     # flush data to disk, set the NoData value and calculate stats
#     outBand.FlushCache()
#     # outBand.SetNoDataValue(-9999)

#     # georeference the image and set the projection
#     outDs.SetGeoTransform(gdal_data.GetGeoTransform())
#     outDs.SetProjection(gdal_data.GetProjection())


class ProcessingWallHeightAscpetAlgorithm(QgsProcessingAlgorithm):

    INPUT_LIMIT = 'INPUT_LIMIT'
    INPUT = 'INPUT'
    OUTPUT_HEIGHT = 'OUTPUT_HEIGHT'
    OUTPUT_ASPECT = 'OUTPUT_ASPECT'
    # ASPECT_BOOL = 'ASPECT_BOOL'


    def initAlgorithm(self, config):

        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT,
            self.tr('Input building and ground DSM'), 
            None, False))
        # self.addParameter(QgsProcessingParameterBoolean(self.ASPECT_BOOL,
        #     self.tr("Calculate wall aspect"),
        #     defaultValue=True)) 
        self.addParameter(QgsProcessingParameterNumber(self.INPUT_LIMIT,
            self.tr("Lower limit for wall height (m)"), 
            QgsProcessingParameterNumber.Double,
            QVariant(3.0),
            minValue=0.0))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_HEIGHT,
            self.tr("Output Wall Height Raster"),
            None, False))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUTPUT_ASPECT,
            self.tr("Output Wall Aspect Raster"), optional=True, createByDefault=False))

    def processAlgorithm(self, parameters, context, feedback):
        outputFileHeight = self.parameterAsOutputLayer(parameters, self.OUTPUT_HEIGHT, context)
        outputFileAspect = self.parameterAsOutputLayer(parameters, self.OUTPUT_ASPECT, context)
        dsmin = self.parameterAsRasterLayer(parameters, self.INPUT, context) 
        # aspectcalculation = self.parameterAsBool(parameters, self.ASPECT_BOOL, context)
        walllimit = self.parameterAsDouble(parameters, self.INPUT_LIMIT, context)

        cmd_folder = Path(os.path.split(inspect.getfile(inspect.currentframe()))[0])
        feedback.setProgressText(str(cmd_folder))
        feedback.setProgressText(str(cmd_folder.parent))
        
        # feedback.setProgressText(str(parameters["INPUT"])) # this prints to the processing log tab
        # QgsMessageLog.logMessage("Testing", "umep", level=Qgis.Info) # This prints to a umep tab
        
        provider = dsmin.dataProvider()
        filepath_dsm = str(provider.dataSourceUri())
        gdal_dsm = gdal.Open(filepath_dsm)
        dsm = gdal_dsm.ReadAsArray().astype(float)
        
        feedback.setProgressText("Calculating wall height")
        total = 100. / (int(dsm.shape[0] * dsm.shape[1]))
        # walls = wa.findwalls(dsm, walllimit, feedback, total)
        walls = wa.findwalls_sp(dsm, walllimit, False)

        wallssave = np.copy(walls)
        # feedback.setProgressText(outputFileHeight)
        saverasternd(gdal_dsm, outputFileHeight, wallssave)
        
        if outputFileAspect:
            total = 100. / 180.0
            # outputFileAspect = self.parameterAsOutputLayer(parameters, self.OUTPUT_ASPECT, context)
            feedback.setProgressText("Calculating wall aspect")
            dirwalls = wa.filter1Goodwin_as_aspect_v3(walls, 1, dsm, feedback, total)
            saverasternd(gdal_dsm, outputFileAspect, dirwalls)
        else:
            feedback.setProgressText("Wall aspect not calculated")
        
        return {self.OUTPUT_HEIGHT: outputFileHeight, self.OUTPUT_ASPECT: outputFileAspect}

    def name(self):
        return 'Urban Geometry: Wall Height and Aspect'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Pre-Processor'

    def shortHelpString(self):
        return self.tr('This algorithm identiies wall pixels and '
            'their height from ground and building digital surface models (DSM) by using a filter as '
            'presented by Lindberg et al. (2015a). Optionally, wall aspect can also be estimated using '
            'a specific linear filter as presented by Goodwin et al. (1999) and further developed by '
            'Lindberg et al. (2015b) to obtain the wall aspect. Wall aspect is given in degrees where '
            'a north facing wall pixel has a value of zero. The output of this plugin is used in other '
            'UMEP plugins such as SEBE (Solar Energy on Building Envelopes) and SOLWEIG (SOlar LongWave '
            'Environmental Irradiance Geometry model).\n'
            '------------------ \n'
            'Goodwin NR, Coops NC, Tooke TR, Christen A, Voogt JA (2009) Characterizing urban surface cover and structure with airborne lidar technology. Can J Remote Sens 35:297–309\n'
            'Lindberg F., Grimmond, C.S.B. and Martilli, A. (2015a) Sunlit fractions on urban facets - Impact of spatial resolution and approach Urban Climate DOI: 10.1016/j.uclim.2014.11.006\n'
            'Lindberg F., Jonsson, P. & Honjo, T. and Wästberg, D. (2015b) Solar energy on building envelopes - 3D modelling in a 2D environment Solar Energy 115 369–378'
            '-------------\n'
            'Full manual available via the <b>Help</b>-button.')

    def helpUrl(self):
        url = 'https://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Geometry%20Wall%20Height%20and%20Aspect.html'
        return url

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def icon(self):
        cmd_folder = Path(os.path.split(inspect.getfile(inspect.currentframe()))[0]).parent
        icon = QIcon(str(cmd_folder) + "/icons/WallsIcon.png")
        return icon

    def createInstance(self):
        return ProcessingWallHeightAscpetAlgorithm()