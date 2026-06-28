# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication, QVariant, QUrl
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterString,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterFolderDestination,
    QgsProcessingOutputString,
    QgsProcessingOutputFolder,
    QgsProcessingOutputFile,
    QgsProcessingOutputHtml,
    QgsFeature,
    QgsFields,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsRectangle,
    QgsWkbTypes,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorFileWriter,
)
import os
import csv
import math
import json
import statistics
from datetime import datetime
from collections import defaultdict, Counter

try:
    import numpy as np
except Exception:
    np = None


class LUCIALynchUrbanComputationalImageAnalyzerPremium(QgsProcessingAlgorithm):
    """Computes a grid-based Urban Legibility Index from five Lynch-inspired elements."""

    BOUNDARY = 'BOUNDARY'
    ROADS = 'ROADS'
    ROAD_CLASS_FIELD = 'ROAD_CLASS_FIELD'
    POI = 'POI'
    POI_CLASS_FIELD = 'POI_CLASS_FIELD'
    BUILDINGS = 'BUILDINGS'
    BUILDING_HEIGHT_FIELD = 'BUILDING_HEIGHT_FIELD'
    BUILDING_OCCUPANCY_FIELD = 'BUILDING_OCCUPANCY_FIELD'
    LANDUSE = 'LANDUSE'
    LANDUSE_FIELD = 'LANDUSE_FIELD'
    EDGE_LINES = 'EDGE_LINES'
    AUTO_EDGE_FROM_ROADS = 'AUTO_EDGE_FROM_ROADS'
    ROAD_EDGE_CLASS_VALUES = 'ROAD_EDGE_CLASS_VALUES'
    NTL_RASTER = 'NTL_RASTER'
    NTL_BAND = 'NTL_BAND'
    NTL_INFLUENCE = 'NTL_INFLUENCE'
    USE_NTL_NODE = 'USE_NTL_NODE'
    USE_NTL_DISTRICT = 'USE_NTL_DISTRICT'
    USE_NTL_LANDMARK = 'USE_NTL_LANDMARK'
    USE_OCCUPANCY_NODE = 'USE_OCCUPANCY_NODE'
    USE_OCCUPANCY_DISTRICT = 'USE_OCCUPANCY_DISTRICT'
    USE_OCCUPANCY_LANDMARK = 'USE_OCCUPANCY_LANDMARK'
    TRANSIT = 'TRANSIT'
    LANDMARKS = 'LANDMARKS'
    LANDMARK_NAME_FIELD = 'LANDMARK_NAME_FIELD'

    GRID_SIZE = 'GRID_SIZE'
    NODE_RADIUS = 'NODE_RADIUS'
    EDGE_BUFFER = 'EDGE_BUFFER'
    LANDMARK_RADIUS = 'LANDMARK_RADIUS'
    MIN_LANDMARK_HEIGHT = 'MIN_LANDMARK_HEIGHT'
    CMAP_SHOW_INFERRED_LANDMARKS = 'CMAP_SHOW_INFERRED_LANDMARKS'
    CMAP_MAX_INFERRED_LANDMARKS = 'CMAP_MAX_INFERRED_LANDMARKS'
    CMAP_INFERRED_LANDMARK_MIN_SCORE = 'CMAP_INFERRED_LANDMARK_MIN_SCORE'
    CMAP_INFERRED_LANDMARK_MIN_SPACING = 'CMAP_INFERRED_LANDMARK_MIN_SPACING'
    CMAP_MAX_MAIN_NODES = 'CMAP_MAX_MAIN_NODES'
    CMAP_NODE_MIN_CENTRALITY = 'CMAP_NODE_MIN_CENTRALITY'
    CMAP_NODE_MIN_SPACING = 'CMAP_NODE_MIN_SPACING'

    W_PATH = 'W_PATH'
    W_EDGE = 'W_EDGE'
    W_DISTRICT = 'W_DISTRICT'
    W_NODE = 'W_NODE'
    W_LANDMARK = 'W_LANDMARK'

    MAKE_PNG = 'MAKE_PNG'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    ADD_TO_PROJECT = 'ADD_TO_PROJECT'

    OUTPUT_FOLDER_PATH = 'OUTPUT_FOLDER_PATH'
    GRID_GPKG = 'GRID_GPKG'
    NODES_GPKG = 'NODES_GPKG'
    SUMMARY_CSV = 'SUMMARY_CSV'
    MANIFEST_JSON = 'MANIFEST_JSON'
    PNG_1 = 'PNG_1'
    PNG_2 = 'PNG_2'
    PNG_3 = 'PNG_3'
    PNG_4 = 'PNG_4'
    PNG_5 = 'PNG_5'
    PNG_6 = 'PNG_6'
    PNG_7 = 'PNG_7'
    PNG_8 = 'PNG_8'
    PNG_9 = 'PNG_9'
    PNG_10 = 'PNG_10'
    PNG_11 = 'PNG_11'
    HTML_REPORT = 'HTML_REPORT'
    GRID_QML = 'GRID_QML'
    NODE_QML = 'NODE_QML'

    def tr(self, string):
        return QCoreApplication.translate('LUCIALynchUrbanComputationalImageAnalyzerPremium', string)

    def createInstance(self):
        return LUCIALynchUrbanComputationalImageAnalyzerPremium()

    def name(self):
        return 'lucia_cityimage'

    def displayName(self):
        return self.tr('LUCIA')

    def shortHelpString(self):
        return self.tr(
            "<p><b>Created By: Maya Safira dan Firman Afrianto</b></p>"

            "<p><b>LUCIA — Lynch Urban Computational Image Analyzer</b> is a QGIS Processing toolbox "
            "for translating Kevin Lynch's five urban image elements into a geospatial diagnostic and "
            "planning-support model. The tool evaluates <b>urban legibility</b>, <b>imageability</b>, "
            "and <b>cognitive structure</b> through five elements: <b>Paths</b>, <b>Edges</b>, "
            "<b>Districts</b>, <b>Nodes</b>, and <b>Landmarks</b>. It generates a regular analysis grid, "
            "element scores, a composite <b>Urban Legibility Index</b>, node hotspot layers, city-image "
            "recommendations, premium PNG maps, CSV summaries, QGIS style files, and an HTML report.</p>"

            "<p><b>Conceptual and methodological note</b></p>"
            "<ul>"
            "<li><b>Research-integrated computational image</b>: combines the previous LUCIA planning-support logic with key ideas from computational Image of the City research: street-network node centrality, path continuity, street-based district thinking, landmark visual-structural-pragmatic salience, and object-oriented composite mapping.</li>"
            "<li><b>Kevin Lynch-based interpretation</b>: outputs are inspired by the five elements of "
            "urban imageability from <i>The Image of the City</i>. They should be interpreted as planning "
            "intelligence, not as a final urban design decision.</li>"
            "<li><b>Computational city image</b>: the tool converts spatial proxies such as road continuity, "
            "edge context, land-use dominance, POI concentration, junctions, transit, building form, "
            "building occupancy/function, landmark points, building height, and optional Nighttime Light into measurable indicators.</li>"
            "<li><b>Context-gated recommendations</b>: recommendations are not assigned simply from the "
            "lowest score. Path, Edge, District, Node, and Landmark actions are only suggested where the "
            "spatial context makes sense.</li>"
            "<li><b>Not a substitute for field observation</b>: results should be checked against local "
            "knowledge, urban design judgment, stakeholder perception, and ground survey.</li>"
            "<li><b>NTL as support layer only</b>: Nighttime Light can strengthen the reading of activity, "
            "emerging nodes, district intensity, and landmark strategic need when the related switches are enabled. It does not replace the five Lynch elements.</li>"
            "</ul>"

            "<p><b>Inputs</b></p>"
            "<ul>"
            "<li><b>Boundary polygon</b>: study area or city boundary used to build the analysis grid.</li>"
            "<li><b>Road / path network line</b>: streets, pedestrian paths, corridors, or other movement "
            "networks used to assess path clarity and node structure.</li>"
            "<li><b>Road class / hierarchy field</b> (recommended): field used to filter Path analysis to "
            "<b>primary</b>, <b>primary_link</b>, <b>secondary</b>, <b>secondary_link</b>, <b>tertiary</b>, <b>tertiary_link</b>, <b>trunk</b>, and <b>trunk_link</b> roads only, matching the idea of legible movement spines.</li>"
            "<li><b>POI points</b> and <b>POI category field</b> (optional): activity concentration and "
            "functional specialization.</li>"
            "<li><b>Building polygons</b> and <b>building height field</b> (optional): built-form intensity, "
            "homogeneity, occupancy/function, and inferred landmark potential.</li>"
            "<li><b>Land use / pola ruang polygons</b> and <b>class field</b> (optional): district identity, "
            "land-use dominance, and thematic continuity.</li>"
            "<li><b>Edge lines</b> (optional): rivers, railways, toll roads, coastline, canals, cliffs, "
            "or other linear barriers/seams. If this input is empty, LUCIA can automatically derive edge candidates from road classes such as motorway, expressway, freeway, or toll road. Trunk and trunk_link are treated as Path classes, not Edge classes.</li>"
            "<li><b>Transit stop / station points</b> (optional): public transport nodes and interchange potential.</li>"
            "<li><b>Manual landmark points</b> (optional): monuments, towers, civic buildings, heritage anchors, "
            "or natural landmarks.</li>"
            "<li><b>Nighttime Light / VIIRS NTL raster</b> (optional): night-time activity support for Node "
            "and District scores.</li>"
            "</ul>"

            "<p><b>Core analysis settings</b></p>"
            "<ul>"
            "<li><b>Analysis grid size</b>: regular grid size in meters.</li>"
            "<li><b>Node influence radius</b>: search radius for junction, POI, transit, and activity-based node support.</li>"
            "<li><b>Edge diagnostic buffer</b>: zone of influence around edge lines.</li>"
            "<li><b>Landmark influence radius</b>: distance-decay influence radius for landmark points.</li>"
            "<li><b>Minimum landmark height</b>: building-height threshold for inferred landmark potential.</li>"
            "<li><b>Element weights</b>: custom weights for Path, Edge, District, Node, and Landmark scores.</li>"
            "<li><b>NTL influence</b>: optional 0–1 adjustment factor for night-time activity support.</li>"
            "<li><b>Use NTL in Node Strength</b>: optional switch to let NTL adjust the final Node score.</li>"
            "<li><b>Use NTL in District Identity</b>: optional switch to let NTL adjust the final District score.</li>"
            "<li><b>Use NTL in Landmark strategic need</b>: optional switch to use NTL as evidence of where landmark reinforcement is strategically needed.</li>"
            "<li><b>Building occupancy/function field</b>: optional building attribute used to distinguish residential, commercial, office, public service, industrial, education, health, tourism, and mixed-use structures.</li>"
            "<li><b>Use occupancy in Node Strength</b>: optional switch to include activity-building share in the raw Node metric.</li>"
            "<li><b>Use occupancy in District Identity</b>: optional switch to include occupancy identity in the District score.</li>"
            "<li><b>Use occupancy in Landmark strategic need</b>: optional switch to use building activity/function as evidence for landmark reinforcement priority.</li>"
            "</ul>"

            "<p><b>Lynch element scoring logic</b></p>"

            "<p><b>A) Path Clarity</b></p>"
            "<ul>"
            "<li>Measures movement structure using road/path density and continuity.</li>"
            "<li>Continuous movement spines are rewarded more than fragmented segments.</li>"
            "<li>When a road-class field is available, Path analysis focuses on <b>primary</b>, <b>secondary</b>, and <b>tertiary</b> roads.</li>"
            "<li>Supports corridor legibility, wayfinding, accessibility, and urban structure diagnosis.</li>"
            "</ul>"

            "<p><b>B) Edge Definition</b></p>"
            "<ul>"
            "<li>Measures the presence and influence of linear barriers, seams, or boundaries.</li>"
            "<li>Uses edge length and buffered edge influence zone.</li>"
            "<li>Edge recommendations are only activated where actual edge context exists.</li>"
            "</ul>"

            "<p><b>C) District Identity</b></p>"
            "<ul>"
            "<li>Measures area character using land-use dominance, entropy, POI specialization, building coverage, "
            "built-form homogeneity, and building occupancy/function pattern.</li>"
            "<li>Supports identification of strong, weak, blurred, or transitional districts.</li>"
            "</ul>"

            "<p><b>D) Node Strength</b></p>"
            "<ul>"
            "<li>Measures strategic urban nodes using genuine road-network junctions, POI concentration, "
            "transit points, building occupancy/activity support, and optional Nighttime Light support.</li>"
            "<li>Designed to detect activity centers, interchange points, local centers, and emerging nodes.</li>"
            "</ul>"

            "<p><b>E) Landmark Visibility</b></p>"
            "<ul>"
            "<li>Measures orientation anchors using manual landmark points, landmark influence radius, "
            "and inferred tall-building potential.</li>"
            "<li>Supports visual reference, city identity, wayfinding, and symbolic-place analysis.</li>"
            "</ul>"

            "<p><b>Urban Legibility Index</b></p>"
            "<p>The composite score is calculated from the five normalized element scores:</p>"
            "<pre>Urban Legibility Index = weighted mean(Path, Edge, District, Node, Landmark)</pre>"
            "<ul>"
            "<li>0–20 = Very Weak</li>"
            "<li>21–40 = Weak</li>"
            "<li>41–60 = Moderate</li>"
            "<li>61–80 = Strong</li>"
            "<li>81–100 = Very Strong</li>"
            "</ul>"

            "<p><b>City Image Intervention logic</b></p>"
            "<ul>"
            "<li><b>Path recommendation</b>: appears where movement demand exists but path clarity is weak.</li>"
            "<li><b>Edge recommendation</b>: appears only near actual edge lines, automatic road-derived edge classes, or edge buffer context.</li>"
            "<li><b>District recommendation</b>: appears where area character, land-use identity, or built-form "
            "coherence needs strengthening.</li>"
            "<li><b>Node recommendation</b>: appears where activity or junction potential exists but node strength is weak.</li>"
            "<li><b>Landmark recommendation</b>: appears where orientation anchors are strategically needed.</li>"
            "<li><b>Maintain</b>: assigned to areas with low intervention priority or already adequate legibility.</li>"
            "</ul>"

            "<p><b>What it produces</b></p>"

            "<p><b>A) Vector outputs</b></p>"
            "<ol>"
            "<li><b>lucia_grid.gpkg</b>: analysis grid with raw metrics, normalized element scores, NTL support fields, "
            "legibility class, building occupancy summary, recommendation theme, recommendation priority, and recommendation text.</li>"
            "<li><b>lucia_node_hotspots.gpkg</b>: detected node hotspot points.</li>"
            "</ol>"

            "<p><b>B) Tabular and report outputs</b></p>"
            "<ol>"
            "<li><b>lucia_summary.csv</b>: summary metrics, mean scores, median score, class counts, and NTL status.</li>"
            "<li><b>lucia_manifest.json</b>: machine-readable list of all output files.</li>"
            "<li><b>lucia_report.html</b>: automatic HTML report with metrics and generated figures.</li>"
            "</ol>"

            "<p><b>C) QGIS style outputs</b></p>"
            "<ol>"
            "<li><b>lucia_grid_legibility_style.qml</b>: default style for Urban Legibility grid.</li>"
            "<li><b>lucia_node_hotspot_style.qml</b>: default style for node hotspot layer.</li>"
            "</ol>"

            "<p><b>D) PNG visualization outputs</b></p>"
            "<ol>"
            "<li><b>01_urban_legibility_index_map.png</b></li>"
            "<li><b>02_five_lynch_elements_composite.png</b></li>"
            "<li><b>03_path_node_network.png</b>: premium path–node diagnostic map with detected junctions, top main nodes, node influence zones, and a clean right-side legend/insight panel.</li>"
            "<li><b>04_district_identity_map.png</b></li>"
            "<li><b>05_edge_barrier_map.png</b></li>"
            "<li><b>06_landmark_visibility_map.png</b></li>"
            "<li><b>07_radar_chart_five_elements.png</b></li>"
            "<li><b>08_planning_recommendation_matrix.png</b></li>"
            "<li><b>09_planning_recommendation_zone_map.png</b></li>"
            "<li><b>10_city_image_intervention_map.png</b>: simplified action map with sidebar insight, top intervention themes, and shape-aware legend.</li>"
            "<li><b>11_computational_city_image_map.png</b>: object-based composite map inspired by computational Image of the City mapping, combining paths, nodes, districts, edges, and landmarks in a single map.</li>"
            "</ol>"

            "<p><b>Output folder behavior</b></p>"
            "<ul>"
            "<li>All deliverables are written into one selected output folder.</li>"
            "<li>The QGIS Results panel returns only the output folder to keep the processing log clean.</li>"
            "<li>A permanent user-selected folder is recommended instead of TEMPORARY_OUTPUT for production runs.</li>"
            "</ul>"

            "<p><b>Important notes</b></p>"
            "<ul>"
            "<li>Input layers should use valid geometries and preferably clean topology.</li>"
            "<li>Very large building layers may increase processing time and memory usage.</li>"
            "<li>Grid size controls the balance between detail, processing time, and map readability.</li>"
            "<li>Manual landmark input is recommended when the study requires strong visual-image interpretation.</li>"
            "<li>NTL influence should usually remain moderate (for example 0.10–0.25) unless the focus is night-time activity.</li>"
            "<li>For reports or publications, disclose that the results are model-derived spatial diagnostics and should be validated locally.</li>"
            "</ul>"

            "<p><b>Dependencies</b></p>"
            "<ul>"
            "<li><b>QGIS Processing framework</b></li>"
            "<li><b>matplotlib</b> for PNG visualization</li>"
            "<li><b>numpy</b> optional but recommended for percentile normalization</li>"
            "</ul>"
        )


    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.BOUNDARY, self.tr('Boundary polygon'), [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.ROADS, self.tr('Road / path network line'), [QgsProcessing.TypeVectorLine]))
        self.addParameter(QgsProcessingParameterField(
            self.ROAD_CLASS_FIELD, self.tr('Road class / hierarchy field (recommended for primary-secondary-tertiary path filtering)'), parentLayerParameterName=self.ROADS, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.POI, self.tr('POI points (optional)'), [QgsProcessing.TypeVectorPoint], optional=True))
        self.addParameter(QgsProcessingParameterField(
            self.POI_CLASS_FIELD, self.tr('POI category/type field (optional)'), parentLayerParameterName=self.POI, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.BUILDINGS, self.tr('Buildings polygon (optional)'), [QgsProcessing.TypeVectorPolygon], optional=True))
        self.addParameter(QgsProcessingParameterField(
            self.BUILDING_HEIGHT_FIELD, self.tr('Building height field (optional)'), parentLayerParameterName=self.BUILDINGS, optional=True))
        self.addParameter(QgsProcessingParameterField(
            self.BUILDING_OCCUPANCY_FIELD, self.tr('Building occupancy / function field (optional)'), parentLayerParameterName=self.BUILDINGS, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.LANDUSE, self.tr('Land use / pola ruang polygon (optional)'), [QgsProcessing.TypeVectorPolygon], optional=True))
        self.addParameter(QgsProcessingParameterField(
            self.LANDUSE_FIELD, self.tr('Land use / pola ruang class field (optional)'), parentLayerParameterName=self.LANDUSE, optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.EDGE_LINES, self.tr('Edge lines: river/rail/toll/coastline/canal etc. (optional)'), [QgsProcessing.TypeVectorLine], optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.AUTO_EDGE_FROM_ROADS, self.tr('Automatically add edge candidates from road hierarchy/classes'), defaultValue=True))
        self.addParameter(QgsProcessingParameterString(
            self.ROAD_EDGE_CLASS_VALUES, self.tr('Road class values treated as Edge candidates'), defaultValue='motorway,motorway_link,expressway,freeway,toll,toll_road'))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.NTL_RASTER, self.tr('Nighttime Light raster / VIIRS NTL (optional)'), optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.NTL_BAND, self.tr('Nighttime Light raster band'), QgsProcessingParameterNumber.Integer, defaultValue=1, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.NTL_INFLUENCE, self.tr('Nighttime Light influence on Node/District scores (0-1)'), QgsProcessingParameterNumber.Double, defaultValue=0.25, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_NTL_NODE, self.tr('Use NTL in Node Strength adjustment'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_NTL_DISTRICT, self.tr('Use NTL in District Identity adjustment'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_NTL_LANDMARK, self.tr('Use NTL in Landmark strategic need / recommendation'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_OCCUPANCY_NODE, self.tr('Use building occupancy in Node Strength'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_OCCUPANCY_DISTRICT, self.tr('Use building occupancy in District Identity'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_OCCUPANCY_LANDMARK, self.tr('Use building occupancy in Landmark strategic need / recommendation'), defaultValue=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.TRANSIT, self.tr('Transit stop / station points (optional)'), [QgsProcessing.TypeVectorPoint], optional=True))
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.LANDMARKS, self.tr('Manual landmark points (optional)'), [QgsProcessing.TypeVectorPoint], optional=True))
        self.addParameter(QgsProcessingParameterField(
            self.LANDMARK_NAME_FIELD, self.tr('Landmark name field (optional)'), parentLayerParameterName=self.LANDMARKS, optional=True))

        self.addParameter(QgsProcessingParameterNumber(
            self.GRID_SIZE, self.tr('Analysis grid size (meters)'), QgsProcessingParameterNumber.Double, defaultValue=250.0, minValue=20.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.NODE_RADIUS, self.tr('Node influence radius (meters)'), QgsProcessingParameterNumber.Double, defaultValue=500.0, minValue=50.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.EDGE_BUFFER, self.tr('Edge diagnostic buffer (meters)'), QgsProcessingParameterNumber.Double, defaultValue=75.0, minValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.LANDMARK_RADIUS, self.tr('Landmark influence radius (meters)'), QgsProcessingParameterNumber.Double, defaultValue=750.0, minValue=50.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.MIN_LANDMARK_HEIGHT, self.tr('Minimum building height to infer landmark (meters)'), QgsProcessingParameterNumber.Double, defaultValue=30.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.CMAP_SHOW_INFERRED_LANDMARKS, self.tr('Computational City Image Map: show inferred landmarks'), defaultValue=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_MAX_INFERRED_LANDMARKS, self.tr('Computational City Image Map: maximum inferred landmarks'), QgsProcessingParameterNumber.Integer, defaultValue=20, minValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_INFERRED_LANDMARK_MIN_SCORE, self.tr('Computational City Image Map: minimum inferred landmark score (0-100)'), QgsProcessingParameterNumber.Double, defaultValue=85.0, minValue=0.0, maxValue=100.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_INFERRED_LANDMARK_MIN_SPACING, self.tr('Computational City Image Map: minimum spacing between inferred landmarks (meters)'), QgsProcessingParameterNumber.Double, defaultValue=750.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_MAX_MAIN_NODES, self.tr('Computational City Image Map: maximum main nodes'), QgsProcessingParameterNumber.Integer, defaultValue=80, minValue=1))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_NODE_MIN_CENTRALITY, self.tr('Computational City Image Map: minimum node centrality (0-1)'), QgsProcessingParameterNumber.Double, defaultValue=0.45, minValue=0.0, maxValue=1.0))
        self.addParameter(QgsProcessingParameterNumber(
            self.CMAP_NODE_MIN_SPACING, self.tr('Computational City Image Map: minimum spacing between main nodes (meters)'), QgsProcessingParameterNumber.Double, defaultValue=350.0, minValue=0.0))

        self.addParameter(QgsProcessingParameterNumber(self.W_PATH, self.tr('Weight: Path Clarity'), QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(self.W_EDGE, self.tr('Weight: Edge Definition'), QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(self.W_DISTRICT, self.tr('Weight: District Identity'), QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(self.W_NODE, self.tr('Weight: Node Strength'), QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))
        self.addParameter(QgsProcessingParameterNumber(self.W_LANDMARK, self.tr('Weight: Landmark Visibility'), QgsProcessingParameterNumber.Double, defaultValue=1.0, minValue=0.0))

        self.addParameter(QgsProcessingParameterBoolean(self.MAKE_PNG, self.tr('Create thematic PNG outputs'), defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(self.ADD_TO_PROJECT, self.tr('Add output vector layers to current project'), defaultValue=True))
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT_FOLDER, self.tr('Output folder')))

        self.addOutput(QgsProcessingOutputFolder(self.OUTPUT_FOLDER_PATH, self.tr('LUCIA output folder')))


    # ---------- Helper methods ----------

    def _safe_float(self, v, default=0.0):
        try:
            if v is None:
                return default
            return float(v)
        except Exception:
            return default

    def _category(self, score):
        if score < 20:
            return 'Very Weak'
        if score < 40:
            return 'Weak'
        if score < 60:
            return 'Moderate'
        if score < 80:
            return 'Strong'
        return 'Very Strong'

    def _local_projected_crs(self, src_crs, geom):
        if src_crs and src_crs.isValid() and not src_crs.isGeographic():
            return src_crs
        try:
            centroid = geom.centroid().asPoint()
            lon, lat = centroid.x(), centroid.y()
            zone = int((lon + 180) / 6) + 1
            epsg = 32600 + zone if lat >= 0 else 32700 + zone
            return QgsCoordinateReferenceSystem(f'EPSG:{epsg}')
        except Exception:
            return QgsCoordinateReferenceSystem('EPSG:3857')

    def _transform_geom(self, geom, transform):
        g = QgsGeometry(geom)
        if transform:
            try:
                g.transform(transform)
            except Exception:
                pass
        try:
            if not g.isGeosValid():
                g = g.makeValid()
        except Exception:
            pass
        return g

    def _collect_geoms(self, source, target_crs, feedback, max_count=None):
        geoms = []
        if source is None:
            return geoms
        tr = None
        if source.sourceCrs() != target_crs:
            tr = QgsCoordinateTransform(source.sourceCrs(), target_crs, QgsProject.instance())
        total = source.featureCount() if source.featureCount() >= 0 else 0
        for i, f in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            if max_count and i >= max_count:
                break
            g = self._transform_geom(f.geometry(), tr)
            if g and not g.isEmpty():
                geoms.append((f, g))
            # Keep the QGIS log readable on very large layers. Earlier builds
            # printed every 1,000 features, which made the Processing log nearly
            # unusable for building layers with hundreds of thousands of features.
            log_step = 50000 if total >= 100000 else (10000 if total >= 25000 else 2500)
            if total and i > 0 and i % log_step == 0:
                feedback.setProgressText(f'Loaded {i:,} / {total:,} features from {source.sourceName()}')
        return geoms

    def _union_boundary(self, source, target_crs):
        tr = None
        if source.sourceCrs() != target_crs:
            tr = QgsCoordinateTransform(source.sourceCrs(), target_crs, QgsProject.instance())
        parts = []
        for f in source.getFeatures():
            g = self._transform_geom(f.geometry(), tr)
            if g and not g.isEmpty():
                parts.append(g)
        if not parts:
            raise QgsProcessingException('Boundary has no valid geometry.')
        u = QgsGeometry.unaryUnion(parts)
        try:
            if not u.isGeosValid():
                u = u.makeValid()
        except Exception:
            pass
        return u

    def _make_grid(self, boundary_geom, grid_size, feedback):
        ext = boundary_geom.boundingBox()
        xmin = math.floor(ext.xMinimum() / grid_size) * grid_size
        xmax = math.ceil(ext.xMaximum() / grid_size) * grid_size
        ymin = math.floor(ext.yMinimum() / grid_size) * grid_size
        ymax = math.ceil(ext.yMaximum() / grid_size) * grid_size
        cells = []
        cols = max(1, int(math.ceil((xmax - xmin) / grid_size)))
        rows = max(1, int(math.ceil((ymax - ymin) / grid_size)))
        total = cols * rows
        n = 0
        for r in range(rows):
            y0 = ymin + r * grid_size
            y1 = y0 + grid_size
            for c in range(cols):
                if feedback.isCanceled():
                    return cells
                x0 = xmin + c * grid_size
                x1 = x0 + grid_size
                rect = QgsGeometry.fromRect(QgsRectangle(x0, y0, x1, y1))
                if not rect.intersects(boundary_geom):
                    continue
                inter = rect.intersection(boundary_geom)
                if inter and not inter.isEmpty() and inter.area() > 1e-6:
                    cells.append({'id': len(cells) + 1, 'geom': inter, 'centroid': inter.pointOnSurface(), 'area': inter.area()})
                n += 1
                if n % 500 == 0:
                    feedback.setProgress(5 + int(20 * n / max(total, 1)))
        return cells

    def _build_index(self, geoms):
        feats = []
        idx = QgsSpatialIndex()
        for i, (f, g) in enumerate(geoms):
            nf = QgsFeature()
            nf.setId(i)
            nf.setGeometry(g)
            feats.append((f, g))
            idx.addFeature(nf)
        return feats, idx

    def _near_count(self, idx, feats, geom, radius):
        if not idx or not feats:
            return 0
        try:
            cpt = geom.pointOnSurface().asPoint()
            rect = QgsRectangle(cpt.x() - radius, cpt.y() - radius, cpt.x() + radius, cpt.y() + radius)
            ids = idx.intersects(rect)
            count = 0
            buf = QgsGeometry.fromPointXY(QgsPointXY(cpt)).buffer(radius, 24)
            for fid in ids:
                if feats[fid][1].intersects(buf):
                    count += 1
            return count
        except Exception:
            return 0

    def _near_weighted(self, idx, feats, center_xy, radius):
        """Distance-decay weighted count of features within radius of center_xy.
        Weight fades linearly from 1.0 (at the center) to 0.0 (at the radius edge),
        instead of the binary in/out cutoff used by _near_count. This better matches
        Lynch's notion that a node's or landmark's influence fades gradually with
        distance rather than switching on/off at an arbitrary boundary."""
        if not idx or not feats or radius <= 0:
            return 0.0
        try:
            cx, cy = center_xy.x(), center_xy.y()
        except Exception:
            cx, cy = center_xy[0], center_xy[1]
        rect = QgsRectangle(cx - radius, cy - radius, cx + radius, cy + radius)
        total = 0.0
        for fid in idx.intersects(rect):
            g = feats[fid][1]
            try:
                pt = g.pointOnSurface().asPoint()
            except Exception:
                continue
            d = math.hypot(pt.x() - cx, pt.y() - cy)
            if d <= radius:
                total += max(0.0, 1.0 - (d / radius))
        return total

    def _detect_junctions(self, roads):
        """Topological junction detector for the Node element.
        A Lynch 'node' is fundamentally a convergence point of paths, not a measure
        of road density. We approximate junctions by counting how many road segment
        endpoints coincide (within a small snapping tolerance) across the whole
        network; coordinates where 3+ segment-ends meet are treated as junctions.
        Returns a list of QgsPointXY junction locations."""
        if not roads:
            return []
        precision = 1.0  # meters, snapping tolerance for endpoint coincidence
        counter = Counter()
        coords = {}
        for _, g in roads:
            try:
                lines = g.asMultiPolyline() if g.isMultipart() else [g.asPolyline()]
            except Exception:
                continue
            for line in lines:
                if not line or len(line) < 2:
                    continue
                for pt in (line[0], line[-1]):
                    key = (round(pt.x() / precision), round(pt.y() / precision))
                    counter[key] += 1
                    coords[key] = pt
        junctions = [coords[k] for k, n in counter.items() if n >= 3]
        return junctions

    def _detect_junctions_ranked(self, roads):
        """Detects topological junctions and assigns a simple structural centrality proxy.
        The paper by Filomena et al. uses centrality to read nodes. Full betweenness
        centrality is expensive and depends on graph libraries, so this lightweight
        implementation keeps LUCIA robust inside QGIS: degree is used as a first-order
        proxy, and the value is normalized to 0..1. The resulting point weights are
        used by Node Strength and the computational city image map."""
        if not roads:
            return []
        precision = 1.0
        counter = Counter()
        coords = {}
        for _, g in roads:
            try:
                lines = g.asMultiPolyline() if g.isMultipart() else [g.asPolyline()]
            except Exception:
                continue
            for line in lines:
                if not line or len(line) < 2:
                    continue
                for pt in (line[0], line[-1]):
                    key = (round(pt.x() / precision), round(pt.y() / precision))
                    counter[key] += 1
                    coords[key] = pt
        if not counter:
            return []
        max_degree = max(counter.values()) if counter else 1
        ranked = []
        for k, degree in counter.items():
            if degree < 3:
                continue
            pt = coords[k]
            centrality = float(degree) / max(float(max_degree), 1.0)
            ranked.append(({'degree': degree, 'centrality': centrality}, QgsGeometry.fromPointXY(QgsPointXY(pt))))
        return ranked

    def _near_weighted_attr(self, idx, feats, center_xy, radius, attr='centrality', default_weight=1.0):
        """Distance-decay weighted count using an optional feature/dict attribute.
        Used for ranked junctions so Node Strength reflects not just junction presence,
        but also the relative structural importance of the junction."""
        if not idx or not feats or radius <= 0:
            return 0.0
        try:
            cx, cy = center_xy.x(), center_xy.y()
        except Exception:
            cx, cy = center_xy[0], center_xy[1]
        rect = QgsRectangle(cx - radius, cy - radius, cx + radius, cy + radius)
        total = 0.0
        for fid in idx.intersects(rect):
            f, g = feats[fid]
            weight = default_weight
            try:
                if isinstance(f, dict):
                    weight = float(f.get(attr, default_weight))
                elif f is not None:
                    weight = float(f[attr])
            except Exception:
                weight = default_weight
            try:
                pt = g.pointOnSurface().asPoint()
            except Exception:
                continue
            d = math.hypot(pt.x() - cx, pt.y() - cy)
            if d <= radius:
                total += weight * max(0.0, 1.0 - (d / radius))
        return total


    def _road_continuity_in_cell(self, idx, feats, cell_geom):
        """Returns (total_length_in_cell, dominant_feature_length_in_cell).
        Used to compute a continuity ratio: a cell traversed by one long, unbroken
        through-road reads as more legible (clear Lynch path) than a cell of equal
        road density made up of many short, disconnected fragments."""
        if not idx or not feats:
            return 0.0, 0.0
        total = 0.0
        per_feature = defaultdict(float)
        for fid in idx.intersects(cell_geom.boundingBox()):
            g = feats[fid][1]
            if g.intersects(cell_geom):
                try:
                    seg_len = g.intersection(cell_geom).length()
                except Exception:
                    seg_len = 0.0
                total += seg_len
                per_feature[fid] += seg_len
        dominant = max(per_feature.values()) if per_feature else 0.0
        return total, dominant

    def _length_in_cell(self, idx, feats, cell_geom):
        if not idx or not feats:
            return 0.0
        total = 0.0
        for fid in idx.intersects(cell_geom.boundingBox()):
            g = feats[fid][1]
            if g.intersects(cell_geom):
                try:
                    total += g.intersection(cell_geom).length()
                except Exception:
                    pass
        return total

    def _count_in_cell(self, idx, feats, cell_geom):
        if not idx or not feats:
            return 0
        count = 0
        for fid in idx.intersects(cell_geom.boundingBox()):
            g = feats[fid][1]
            if g.intersects(cell_geom):
                count += 1
        return count

    def _building_stats_in_cell(self, idx, feats, cell_geom, height_field, occupancy_field=''):
        if not idx or not feats:
            return 0, 0.0, 0.0, 0, 0.0, 'No data', 0.0, 0.0, 0, 0.0, 0.0, 0.0
        count = 0
        area = 0.0
        height_max = 0.0
        tall = 0
        footprints = []
        occ_areas = defaultdict(float)

        activity_keywords = (
            'commercial', 'retail', 'shop', 'mall', 'market', 'office', 'business',
            'public', 'civic', 'government', 'school', 'education', 'university',
            'hospital', 'health', 'clinic', 'hotel', 'tourism', 'restaurant', 'cafe',
            'transport', 'station', 'terminal', 'industrial', 'warehouse', 'mixed',
            'perdagangan', 'jasa', 'kantor', 'pendidikan', 'kesehatan', 'pasar',
            'komersial', 'fasilitas', 'publik'
        )
        residential_keywords = (
            'residential', 'house', 'housing', 'home', 'apartment', 'apartemen',
            'rumah', 'hunian', 'permukiman', 'kampung'
        )

        activity_area = 0.0
        residential_area = 0.0
        for fid in idx.intersects(cell_geom.boundingBox()):
            f, g = feats[fid]
            if not g.intersects(cell_geom):
                continue
            count += 1
            fp_area = 0.0
            try:
                fp_area = g.intersection(cell_geom).area()
                area += fp_area
            except Exception:
                pass
            footprints.append(fp_area)
            h = self._safe_float(f[height_field], 0.0) if height_field else 0.0
            if h > height_max:
                height_max = h

            if occupancy_field:
                try:
                    occ_val = f[occupancy_field]
                except Exception:
                    occ_val = None
                occ = str(occ_val).strip() if occ_val not in (None, '') else 'Unknown'
                occ_areas[occ] += fp_area
                occ_low = occ.lower()
                if any(k in occ_low for k in activity_keywords):
                    activity_area += fp_area
                if any(k in occ_low for k in residential_keywords):
                    residential_area += fp_area

        # Footprint-size homogeneity: a district with visually coherent, similarly
        # sized buildings reads as a stronger Lynch "district" than one with wildly
        # mixed footprint scales, even at the same coverage ratio. We use the
        # inverse coefficient of variation, normalized to 0..1.
        homogeneity = 0.0
        if len(footprints) >= 2:
            mean_fp = statistics.mean(footprints) if footprints else 0.0
            if mean_fp > 1e-6:
                try:
                    cv = statistics.pstdev(footprints) / mean_fp
                    homogeneity = 1.0 / (1.0 + cv)
                except Exception:
                    homogeneity = 0.0

        occ_dom = 'No data'
        occ_dom_pct = 0.0
        occ_entropy = 0.0
        occ_classes = 0
        occ_identity = homogeneity
        if occ_areas and area > 1e-9:
            occ_dom, dom_area = max(occ_areas.items(), key=lambda kv: kv[1])
            occ_dom_pct = dom_area / max(area, 1e-9)
            occ_classes = len(occ_areas)
            entropy = 0.0
            for a in occ_areas.values():
                p = a / max(area, 1e-9)
                if p > 0:
                    entropy -= p * math.log(p)
            max_entropy = math.log(max(occ_classes, 1)) if occ_classes > 1 else 1.0
            occ_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
            occ_identity = (0.62 * occ_dom_pct) + (0.38 * (1.0 - occ_entropy))

        occ_activity = activity_area / max(area, 1e-9) if area > 1e-9 else 0.0
        occ_res_share = residential_area / max(area, 1e-9) if area > 1e-9 else 0.0

        return count, area, height_max, tall, homogeneity, occ_dom, occ_dom_pct, occ_entropy, occ_classes, occ_activity, occ_res_share, occ_identity


    def _poi_stats_in_cell(self, idx, feats, cell_geom, class_field):
        count = 0
        cls = Counter()
        if not idx or not feats:
            return count, cls
        for fid in idx.intersects(cell_geom.boundingBox()):
            f, g = feats[fid]
            if g.intersects(cell_geom):
                count += 1
                if class_field:
                    val = str(f[class_field]) if f[class_field] is not None else 'Unknown'
                    cls[val] += 1
        return count, cls

    def _landuse_stats(self, idx, feats, cell_geom, lu_field):
        if not idx or not feats:
            return 'No data', 0.0, 0.0, 0
        areas = defaultdict(float)
        total_area = 0.0
        for fid in idx.intersects(cell_geom.boundingBox()):
            f, g = feats[fid]
            if not g.intersects(cell_geom):
                continue
            try:
                ia = g.intersection(cell_geom).area()
            except Exception:
                ia = 0.0
            if ia <= 0:
                continue
            klass = str(f[lu_field]) if lu_field and f[lu_field] is not None else 'Land use'
            areas[klass] += ia
            total_area += ia
        if total_area <= 0:
            return 'No data', 0.0, 0.0, 0
        dom_class, dom_area = max(areas.items(), key=lambda kv: kv[1])
        dominance = dom_area / total_area
        entropy = 0.0
        for a in areas.values():
            p = a / total_area
            if p > 0:
                entropy -= p * math.log(p)
        max_entropy = math.log(max(len(areas), 1)) if len(areas) > 1 else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
        return dom_class, dominance, normalized_entropy, len(areas)

    def _build_edge_buffer_zone(self, edges, edge_buffer):
        """Dissolve all edge lines into a single buffered zone. Lynch edges act as
        barriers/seams whose effect extends laterally into the blocks they border
        (a river or rail line shapes the legibility of land on both sides of it),
        not only the exact strip of ground the line crosses. EDGE_BUFFER controls
        how wide that zone of influence is."""
        if not edges or edge_buffer <= 0:
            return None
        try:
            parts = [g.buffer(edge_buffer, 8) for _, g in edges]
            return QgsGeometry.unaryUnion(parts)
        except Exception:
            return None

    def _pct_norm(self, values, invert=False):
        vals = [v for v in values if v is not None and math.isfinite(v)]
        if not vals:
            return [0.0 for _ in values]
        if np:
            lo = float(np.percentile(vals, 5))
            hi = float(np.percentile(vals, 95))
        else:
            sv = sorted(vals)
            lo = sv[int(0.05 * (len(sv) - 1))]
            hi = sv[int(0.95 * (len(sv) - 1))]
        if abs(hi - lo) < 1e-9:
            return [50.0 if v and v > 0 else 0.0 for v in values]
        out = []
        for v in values:
            s = 100.0 * (v - lo) / (hi - lo)
            s = max(0.0, min(100.0, s))
            if invert:
                s = 100.0 - s
            out.append(s)
        return out

    def _write_csv(self, path, rows):
        with open(path, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f)
            w.writerow(['metric', 'value'])
            for k, v in rows:
                w.writerow([k, v])

    def _memory_layer(self, geometry_name, crs, fields, layer_name):
        layer = QgsVectorLayer(f'{geometry_name}?crs={crs.authid()}', layer_name, 'memory')
        if not layer.isValid():
            raise QgsProcessingException(f'Could not create memory layer: {layer_name}')
        dp = layer.dataProvider()
        dp.addAttributes(fields)
        layer.updateFields()
        return layer

    def _write_layer_to_gpkg(self, layer, path, layer_name):
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName = 'GPKG'
        opts.fileEncoding = 'UTF-8'
        opts.layerName = layer_name
        opts.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer if os.path.exists(path) else QgsVectorFileWriter.CreateOrOverwriteFile
        err = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, QgsProject.instance().transformContext(), opts)
        try:
            status = err[0]
            message = err[1] if len(err) > 1 else ''
        except Exception:
            status = err
            message = ''
        if status != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f'Failed to write {layer_name} to GPKG: {message}')
        return path

    def _add_file_link(self, feedback, label, path):
        """QGIS Processing logs in some builds do not render HTML anchors, so
        this function intentionally prints a clean plain-text folder path only.
        The clickable folder is exposed through QgsProcessingOutputFolder in the
        Results panel; the log stays readable and no longer shows raw <a href>.
        """
        if not path:
            return
        norm = os.path.abspath(path)
        feedback.pushInfo(f'{label}: {norm}')


    def _geom_bounds(self, geom):
        bb = geom.boundingBox()
        return bb.xMinimum(), bb.xMaximum(), bb.yMinimum(), bb.yMaximum()

    def _set_map_extent(self, ax, boundary_geom, pad_ratio=0.05):
        xmin, xmax, ymin, ymax = self._geom_bounds(boundary_geom)
        dx = max((xmax - xmin) * pad_ratio, 1.0)
        dy = max((ymax - ymin) * pad_ratio, 1.0)
        ax.set_xlim(xmin - dx, xmax + dx)
        ax.set_ylim(ymin - dy, ymax + dy)
        ax.set_aspect('equal', 'box')
        ax.axis('off')

    def _plot_polygon_geom(self, ax, geom, facecolor=None, edgecolor='#666666', linewidth=0.1, alpha=1.0, zorder=1):
        try:
            if geom.isMultipart():
                polys = geom.asMultiPolygon()
                for poly in polys:
                    if not poly:
                        continue
                    ring = poly[0]
                    xs = [p.x() for p in ring]
                    ys = [p.y() for p in ring]
                    ax.fill(xs, ys, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, alpha=alpha, zorder=zorder)
            else:
                poly = geom.asPolygon()
                if poly:
                    ring = poly[0]
                    xs = [p.x() for p in ring]
                    ys = [p.y() for p in ring]
                    ax.fill(xs, ys, facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, alpha=alpha, zorder=zorder)
        except Exception:
            pass

    def _plot_line_geom(self, ax, geom, color='#222222', linewidth=0.5, alpha=0.8, zorder=2):
        try:
            if geom.isMultipart():
                lines = geom.asMultiPolyline()
                for line in lines:
                    if not line:
                        continue
                    ax.plot([p.x() for p in line], [p.y() for p in line], color=color, linewidth=linewidth, alpha=alpha, zorder=zorder)
            else:
                line = geom.asPolyline()
                if line:
                    ax.plot([p.x() for p in line], [p.y() for p in line], color=color, linewidth=linewidth, alpha=alpha, zorder=zorder)
        except Exception:
            pass

    def _point_xy(self, geom):
        try:
            pt = geom.asPoint()
            return pt.x(), pt.y()
        except Exception:
            try:
                pt = geom.pointOnSurface().asPoint()
                return pt.x(), pt.y()
            except Exception:
                return None, None


    def _select_main_nodes_for_cmap(self, junctions, max_count=80, min_centrality=0.45, min_spacing=350.0):
        """Selects a reduced set of major junctions for the Computational City Image Map.
        Nodes in Lynchian mapping should be focused and memorable; therefore this method
        keeps only high-centrality junctions and enforces a minimum spacing to avoid clutter."""
        if not junctions:
            return []
        candidates = []
        for meta, g in junctions:
            try:
                pt = g.asPoint() if hasattr(g, 'asPoint') else g.pointOnSurface().asPoint()
            except Exception:
                continue
            c = 0.0
            d = 0
            try:
                c = float(meta.get('centrality', 0.0)) if isinstance(meta, dict) else float(meta['centrality'])
            except Exception:
                c = 0.0
            try:
                d = int(meta.get('degree', 0)) if isinstance(meta, dict) else int(meta['degree'])
            except Exception:
                d = 0
            if c >= min_centrality:
                candidates.append((c, d, pt))
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        selected = []
        for c, d, pt in candidates:
            keep = True
            for spt in selected:
                if math.hypot(pt.x() - spt.x(), pt.y() - spt.y()) < max(0.0, min_spacing):
                    keep = False
                    break
            if keep:
                selected.append(pt)
                if len(selected) >= max_count:
                    break
        return selected

    def _select_inferred_landmarks_for_cmap(self, cells, min_score=85.0, max_count=20, min_spacing=750.0):
        """Select a small, well-spaced set of inferred landmarks.
        Landmark candidates are taken only from cells with high landmark score and no
        manual landmark point, then thinned spatially so the final map contains only
        a few salient anchors instead of a dense red field."""
        if not cells or max_count <= 0:
            return []
        candidates = []
        for cell in cells:
            try:
                score = float(cell.get('landmark_score', 0.0))
            except Exception:
                score = 0.0
            if score < min_score:
                continue
            if int(cell.get('lm_n', 0)) > 0:
                continue
            try:
                pt = cell['centroid'].asPoint()
            except Exception:
                continue
            # Prefer truly salient cells: score first, then height and occupancy activity
            h = float(cell.get('height_max', 0.0))
            occ = float(cell.get('occ_activity', 0.0))
            poi_n = int(cell.get('poi_n', 0))
            candidates.append((score, h, occ, poi_n, pt))
        candidates.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
        selected = []
        selected_pts = []
        for score, h, occ, poi_n, pt in candidates:
            keep = True
            for spt in selected_pts:
                if math.hypot(pt.x() - spt.x(), pt.y() - spt.y()) < max(0.0, min_spacing):
                    keep = False
                    break
            if keep:
                selected.append(pt)
                selected_pts.append(pt)
                if len(selected) >= max_count:
                    break
        return selected

    def _draw_boundary_outline(self, ax, boundary_geom, color='#1a1a1a', linewidth=1.1):
        """Draws the study-area boundary as a crisp outline on top of the grid so
        every map reads as a bounded place, not a loose block of colored cells."""
        try:
            if boundary_geom.isMultipart():
                polys = boundary_geom.asMultiPolygon()
            else:
                polys = [boundary_geom.asPolygon()]
            for poly in polys:
                if not poly:
                    continue
                for ring in poly:
                    if not ring:
                        continue
                    ax.plot([p.x() for p in ring], [p.y() for p in ring], color=color, linewidth=linewidth, alpha=0.95, zorder=5)
        except Exception:
            pass

    def _draw_scalebar(self, ax, boundary_geom):
        """Scale bar anchored to the literal bottom-left corner of the axes
        (axes-fraction coordinates), with an opaque backing panel, instead of
        the previous data-bbox positioning — which placed the bar wherever the
        boundary's bounding-box corner happened to fall, often on top of
        colored map cells for irregularly-shaped boundaries."""
        try:
            xmin, xmax, ymin, ymax = self._geom_bounds(boundary_geom)
            span = xmax - xmin
            if span <= 0:
                return
            raw = span * 0.18
            magnitude = 10 ** math.floor(math.log10(max(raw, 1.0)))
            for mult in (1, 2, 2.5, 5, 10):
                candidate = mult * magnitude
                if candidate >= raw:
                    bar_len = candidate
                    break
            else:
                bar_len = magnitude
            xlim = ax.get_xlim()
            data_span = xlim[1] - xlim[0]
            if data_span <= 0:
                return
            bar_frac = bar_len / data_span
            x0, y0 = 0.045, 0.065
            from matplotlib.patches import FancyBboxPatch
            panel = FancyBboxPatch((x0 - 0.025, y0 - 0.030), bar_frac + 0.06, 0.085,
                                    boxstyle='round,pad=0.004,rounding_size=0.012',
                                    transform=ax.transAxes, facecolor='white', edgecolor='none',
                                    alpha=0.88, zorder=9)
            ax.add_patch(panel)
            ax.plot([x0, x0 + bar_frac], [y0, y0], transform=ax.transAxes, color='#1a1a1a',
                    linewidth=2.5, zorder=10, solid_capstyle='butt')
            for xt in (x0, x0 + bar_frac):
                ax.plot([xt, xt], [y0 - 0.013, y0 + 0.013], transform=ax.transAxes,
                        color='#1a1a1a', linewidth=1.4, zorder=10)
            label = f'{bar_len / 1000:.1f} km' if bar_len >= 1000 else f'{bar_len:.0f} m'
            ax.text(x0 + bar_frac / 2.0, y0 + 0.022, label, transform=ax.transAxes,
                    ha='center', va='bottom', fontsize=8.5, zorder=10, color='#1a1a1a')
        except Exception:
            pass

    def _add_watermark(self, fig):
        """Small generated-by / date footer printed on every PNG for traceability."""
        try:
            stamp = datetime.now().strftime('%Y-%m-%d')
            fig.text(0.995, 0.005, f'LUCIA · generated {stamp} · Maya Safira & Firman Afrianto', ha='right', va='bottom',
                      fontsize=7, color='#888888', alpha=0.85)
        except Exception:
            pass

    def _mean_scores(self, cells):
        return {
            'Path': statistics.mean([c['path_score'] for c in cells]) if cells else 0.0,
            'Edge': statistics.mean([c['edge_score'] for c in cells]) if cells else 0.0,
            'District': statistics.mean([c['district_score'] for c in cells]) if cells else 0.0,
            'Node': statistics.mean([c['node_score'] for c in cells]) if cells else 0.0,
            'Landmark': statistics.mean([c['landmark_score'] for c in cells]) if cells else 0.0,
            'Legibility': statistics.mean([c['legibility'] for c in cells]) if cells else 0.0,
        }

    def _score_to_recommendation(self, theme, value):
        if theme == 'Path':
            if value < 40:
                return 'Strengthen corridor continuity, wayfinding, and multimodal links.'
            if value < 60:
                return 'Improve path hierarchy and enhance key connectors.'
            return 'Maintain and protect the strongest movement spines.'
        if theme == 'Edge':
            if value < 40:
                return 'Clarify urban boundaries and improve edge treatment.'
            if value < 60:
                return 'Add crossing points and soften barrier effects where needed.'
            return 'Preserve strong edges while managing permeability.'
        if theme == 'District':
            if value < 40:
                return 'Strengthen district identity through land-use coherence and placemaking.'
            if value < 60:
                return 'Reinforce character-defining uses and improve transitions.'
            return 'Capitalize on distinctive district identity in planning and branding.'
        if theme == 'Node':
            if value < 40:
                return 'Create or intensify local centers with public facilities and access.'
            if value < 60:
                return 'Improve node visibility, comfort, and pedestrian integration.'
            return 'Consolidate strong nodes as service and transit anchors.'
        if theme == 'Landmark':
            if value < 40:
                return 'Introduce or highlight orientation anchors and civic markers.'
            if value < 60:
                return 'Improve landmark visibility and spatial linkage to key routes.'
            return 'Protect landmark viewsheds and reinforce symbolic identity.'
        return 'Review the spatial structure and refine planning priorities.'

    def _sample_raster_at_point(self, raster_layer, pt, band=1, transform=None):
        """Samples an optional Nighttime Light raster at a projected analysis point.
        This is intentionally lightweight (centroid sampling) so the toolbox stays
        fast and robust on large city grids. NTL is used as a support signal for
        night-time activity and imageability, not as a replacement for the five
        Lynch elements."""
        if raster_layer is None:
            return None
        try:
            qpt = QgsPointXY(pt.x(), pt.y())
        except Exception:
            try:
                qpt = QgsPointXY(pt[0], pt[1])
            except Exception:
                return None
        try:
            if transform is not None:
                qpt = transform.transform(qpt)
        except Exception:
            pass
        try:
            provider = raster_layer.dataProvider()
            value, ok = provider.sample(qpt, int(band))
            if not ok or value is None:
                return None
            value = float(value)
            if not math.isfinite(value):
                return None
            try:
                nd = provider.sourceNoDataValue(int(band))
                if nd is not None and math.isfinite(float(nd)) and abs(value - float(nd)) < 1e-9:
                    return None
            except Exception:
                pass
            return value
        except Exception:
            return None

    def _guess_road_class_field(self, geoms):
        """Tries to guess a road hierarchy field from common OSM-style names."""
        if not geoms:
            return ''
        try:
            sample_f = geoms[0][0]
            names = [fld.name() for fld in sample_f.fields()]
        except Exception:
            return ''
        lookup = {n.lower(): n for n in names}
        for cand in ['highway', 'fclass', 'class', 'road_class', 'road_type', 'type']:
            if cand in lookup:
                return lookup[cand]
        return ''

    def _filter_path_roads(self, geoms, class_field, feedback):
        """Filters Path and Node road inputs to primary/secondary/tertiary roads."""
        if not geoms:
            return geoms
        field_name = class_field or self._guess_road_class_field(geoms)
        if not field_name:
            feedback.pushInfo('No road class field was provided/found. Path analysis will use all roads.')
            return geoms
        allowed = {'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'trunk', 'trunk_link'}
        filtered = []
        for f, g in geoms:
            try:
                raw = f[field_name]
            except Exception:
                raw = None
            if raw is None:
                continue
            if str(raw).strip().lower() in allowed:
                filtered.append((f, g))
        if filtered:
            feedback.pushInfo(f'Path analysis road filter applied on field "{field_name}": {len(filtered):,} of {len(geoms):,} roads kept (primary, primary_link, secondary, secondary_link, tertiary, tertiary_link, trunk, trunk_link).')
            return filtered
        feedback.pushInfo(f'Road class field "{field_name}" was found, but no primary/secondary/tertiary values were matched. Using all roads instead.')
        return geoms

    def _filter_edge_roads(self, geoms, class_field, edge_class_values, feedback):
        """Extracts road-derived Edge candidates from the road layer.
        In Lynch's framework, motorways, expressways, toll roads,
        and similar high-capacity corridors can work as edges/barriers rather
        than ordinary paths. This method is used whether the manual EDGE_LINES
        input is empty or filled; manual edges and road-derived edges are combined."""
        if not geoms:
            return []
        field_name = class_field or self._guess_road_class_field(geoms)
        if not field_name:
            feedback.pushInfo('Automatic road-derived Edge extraction skipped: no road class field was provided/found.')
            return []

        if edge_class_values:
            classes = {v.strip().lower() for v in str(edge_class_values).replace(';', ',').split(',') if v.strip()}
        else:
            classes = set()
        if not classes:
            classes = {'motorway', 'motorway_link', 'expressway', 'freeway', 'toll', 'toll_road'}

        edge_geoms = []
        for f, g in geoms:
            try:
                raw = f[field_name]
            except Exception:
                raw = None
            if raw is None:
                continue
            v = str(raw).strip().lower()
            if v in classes:
                edge_geoms.append((f, g))

        if edge_geoms:
            feedback.pushInfo(f'Automatic road-derived Edge extraction on field "{field_name}": {len(edge_geoms):,} roads added as Edge candidates ({", ".join(sorted(classes))}).')
        else:
            feedback.pushInfo(f'Automatic road-derived Edge extraction found no matching roads in field "{field_name}" for: {", ".join(sorted(classes))}.')
        return edge_geoms

    def _cell_recommendation_v6(self, cell, ps, es, ds, ns, ls, nts, leg, use_ntl_node=True, use_ntl_district=True, use_ntl_landmark=True, use_occupancy_node=True, use_occupancy_district=True, use_occupancy_landmark=True):
        """Context-gated city-image recommendation logic.

        Lynch elements are not all area phenomena. v6 therefore does not simply
        choose the lowest score. It first checks whether the element makes sense
        in the cell's context: Edge requires actual edge context; Node requires
        activity/junction potential; Landmark requires strategic orientation
        demand; District requires area-character context; Path requires movement
        demand. This prevents maps where every low-edge-score cell becomes
        "Edge" or where node problems spread into empty areas.
        """
        edge_context = float(cell.get('edge_context', 0.0))
        poi_n = float(cell.get('poi_n', 0.0))
        bldg_cov = float(cell.get('bldg_cov', 0.0))
        junction_near = float(cell.get('junction_near', 0.0))
        lu_classes = float(cell.get('lu_classes', 0.0))
        occ_activity = float(cell.get('occ_activity', 0.0))
        occ_res_share = float(cell.get('occ_res_share', 0.0))
        occ_identity = float(cell.get('occ_identity', 0.0))

        ntl_node_support = (nts / 100.0) if use_ntl_node else 0.0
        ntl_district_support = (nts / 100.0) if use_ntl_district else 0.0
        ntl_landmark_support = (nts / 100.0) if use_ntl_landmark else 0.0
        occ_node_support = occ_activity if use_occupancy_node else 0.0
        occ_district_identity = occ_identity if use_occupancy_district else 0.0
        occ_district_res = occ_res_share if use_occupancy_district else 0.0
        occ_landmark_support = occ_activity if use_occupancy_landmark else 0.0

        activity_support = max(
            ntl_node_support,
            occ_node_support,
            min(1.0, poi_n / 8.0),
            min(1.0, junction_near / 4.0),
            min(1.0, bldg_cov * 3.0),
            ds / 100.0
        )
        movement_demand = max(activity_support, ns / 100.0, ds / 100.0)
        district_context = max(min(1.0, lu_classes / 3.0), min(1.0, poi_n / 10.0), min(1.0, bldg_cov * 3.0), occ_district_identity, occ_district_res, ntl_district_support)
        node_potential = max(min(1.0, junction_near / 5.0), min(1.0, poi_n / 12.0), ntl_node_support, occ_node_support)
        landmark_strategic = max(ns / 100.0, ds / 100.0, ps / 100.0, ntl_landmark_support, occ_landmark_support)

        candidates = {}
        # Path is a corridor/accessibility problem; it needs movement demand.
        if movement_demand >= 0.22:
            candidates['Path'] = max(0.0, 62.0 - ps) * (0.45 + 0.55 * movement_demand)

        # Edge is only valid around actual rivers/rail/coast/toll/etc. or their buffer.
        if edge_context >= 0.05:
            candidates['Edge'] = max(0.0, 62.0 - es) * (0.35 + 0.65 * min(1.0, edge_context))

        # District is area-based; it needs land-use/POI/built-form context.
        if district_context >= 0.25:
            candidates['District'] = max(0.0, 64.0 - ds) * (0.40 + 0.60 * district_context)

        # Node is a point/catchment problem; it needs activity or network convergence potential.
        if node_potential >= 0.28:
            candidates['Node'] = max(0.0, 64.0 - ns) * (0.35 + 0.65 * node_potential)

        # Landmark should appear where orientation anchors are strategically needed.
        if landmark_strategic >= 0.42:
            candidates['Landmark'] = max(0.0, 62.0 - ls) * (0.30 + 0.70 * landmark_strategic)

        if not candidates:
            # Dense urban cells should not disappear into a white void only because
            # the gating thresholds are strict. If the area has clear urban context
            # and middling/weak legibility, give a soft fallback recommendation.
            urban_context = max(activity_support, district_context, node_potential, movement_demand)
            if urban_context >= 0.28 and leg < 62:
                if district_context >= max(movement_demand, node_potential):
                    return 'District', max(25.0, 68.0 - leg), 'Strengthen district identity, character continuity, and area coherence.'
                if movement_demand >= node_potential:
                    return 'Path', max(25.0, 66.0 - leg), 'Clarify the main movement spine, hierarchy, and wayfinding structure.'
                return 'Node', max(25.0, 66.0 - leg), 'Create or intensify a local center and improve access, activity focus, and node clarity.'
            return 'Maintain', max(0.0, 100.0 - leg), 'Maintain and monitor existing city-image structure.'

        theme, need = max(candidates.items(), key=lambda kv: kv[1])
        priority = max(0.0, min(100.0, (100.0 - leg) * 0.60 + need * 1.10))

        # Avoid overstating action in already legible cells, but do not hide
        # moderate/weak urban core areas completely.
        if (priority < 28 and leg >= 60) or (leg >= 72 and need < 25):
            return 'Maintain', max(0.0, 100.0 - leg), 'Maintain and consolidate existing city-image structure.'

        return theme, priority, self._score_to_recommendation(theme, {
            'Path': ps, 'Edge': es, 'District': ds, 'Node': ns, 'Landmark': ls
        }.get(theme, 0.0))

    def _rec_theme_color(self, theme):
        palette = {
            'Path': '#2563eb',
            'Edge': '#f97316',
            'District': '#16a34a',
            'Node': '#7c3aed',
            'Landmark': '#dc2626',
            'Maintain': '#64748b',
        }
        return palette.get(theme, '#64748b')

    def _rec_theme_zone_color(self, theme):
        palette = {
            'Path': '#8fb0f6',
            'Edge': '#f6b37e',
            'District': '#83cf9e',
            'Node': '#c3acf8',
            'Landmark': '#f4a3a3',
            'Maintain': '#d5dde7',
        }
        return palette.get(theme, '#d5dde7')

    def _smooth_recommendation_themes(self, cells, grid_size):
        """Spatially smooths the recommendation theme to avoid a noisy pixel-like
        checkerboard map. The theme is decided by a weighted neighborhood vote,
        using recommendation priority and distance decay. This keeps local
        planning zones coherent while preserving the underlying grid detail."""
        if not cells:
            return
        try:
            idx = QgsSpatialIndex()
            feats = []
            for i, cell in enumerate(cells):
                f = QgsFeature()
                f.setId(i)
                f.setGeometry(cell['centroid'])
                idx.addFeature(f)
                feats.append(f)

            radius = max(float(grid_size) * 3.0, 750.0)
            for i, cell in enumerate(cells):
                try:
                    cp = cell['centroid'].asPoint()
                except Exception:
                    cp = cell['centroid'].pointOnSurface().asPoint()
                rect = QgsRectangle(cp.x() - radius, cp.y() - radius, cp.x() + radius, cp.y() + radius)
                votes = defaultdict(float)
                priorities = []
                for fid in idx.intersects(rect):
                    nb = cells[fid]
                    try:
                        npnt = nb['centroid'].asPoint()
                    except Exception:
                        npnt = nb['centroid'].pointOnSurface().asPoint()
                    d = math.hypot(npnt.x() - cp.x(), npnt.y() - cp.y())
                    if d > radius:
                        continue
                    decay = 1.0 - (d / radius)
                    pr = max(1.0, float(nb.get('rec_priority', 0.0)))
                    votes[nb.get('rec_theme', 'Path')] += pr * (0.25 + 0.75 * decay)
                    priorities.append(pr * (0.25 + 0.75 * decay))
                if votes:
                    cell['rec_theme_smooth'] = max(votes.items(), key=lambda kv: kv[1])[0]
                    cell['rec_priority_smooth'] = max(0.0, min(100.0, statistics.mean(priorities) if priorities else cell.get('rec_priority', 0.0)))
                else:
                    cell['rec_theme_smooth'] = cell.get('rec_theme', 'Path')
                    cell['rec_priority_smooth'] = cell.get('rec_priority', 0.0)
        except Exception:
            for cell in cells:
                cell['rec_theme_smooth'] = cell.get('rec_theme', 'Path')
                cell['rec_priority_smooth'] = cell.get('rec_priority', 0.0)

    def _fallback_chart(self, path, title, reason=''):
        """Writes a minimal placeholder PNG so a single chart failure never takes
        down the rest of the PNG suite (mirrors the safety pattern used in the
        other LUCIA-family plugins)."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig = plt.figure(figsize=(10, 6), dpi=150)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis('off')
            ax.text(0.5, 0.55, title, ha='center', va='center', fontsize=16, fontweight='bold')
            ax.text(0.5, 0.42, 'Chart could not be generated for this dataset.', ha='center', va='center', fontsize=10, color='#666666')
            fig.savefig(path, bbox_inches='tight')
            plt.close(fig)
        except Exception:
            pass

    def _create_png_outputs(self, out_folder, cells, boundary_geom, roads, edges, landmarks, junctions, junction_pts, hotspot_points, grid_size, feedback, cmap_show_inferred_landmarks=True, cmap_max_inferred_landmarks=20, cmap_inferred_landmark_min_score=85.0, cmap_inferred_landmark_min_spacing=750.0, cmap_max_main_nodes=80, cmap_node_min_centrality=0.45, cmap_node_min_spacing=350.0):
        paths = {
            'png1': os.path.join(out_folder, '01_urban_legibility_index_map.png'),
            'png2': os.path.join(out_folder, '02_five_lynch_elements_composite.png'),
            'png3': os.path.join(out_folder, '03_path_node_network.png'),
            'png4': os.path.join(out_folder, '04_district_identity_map.png'),
            'png5': os.path.join(out_folder, '05_edge_barrier_map.png'),
            'png6': os.path.join(out_folder, '06_landmark_visibility_map.png'),
            'png7': os.path.join(out_folder, '07_radar_chart_five_elements.png'),
            'png8': os.path.join(out_folder, '08_planning_recommendation_matrix.png'),
            'png9': os.path.join(out_folder, '09_planning_recommendation_zone_map.png'),
            'png10': os.path.join(out_folder, '10_city_image_intervention_map.png'),
            'png11': os.path.join(out_folder, '11_computational_city_image_map.png'),
        }
        titles = {
            'png1': 'Urban Legibility Index Map',
            'png2': 'Five Lynch Elements Composite',
            'png3': 'Path–Node Network',
            'png4': 'District Identity Map',
            'png5': 'Edge Barrier Map',
            'png6': 'Landmark Visibility Map',
            'png7': 'Radar Chart — Five Lynch Elements',
            'png8': 'Planning Recommendation Matrix',
            'png9': 'Planning Recommendation Zone Map',
            'png10': 'City Image Action Map',
            'png11': 'Computational City Image Map',
        }

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.colors import Normalize
            from matplotlib.patches import FancyBboxPatch, Rectangle
            import textwrap as _textwrap
        except Exception as e:
            feedback.pushWarning(f'PNG outputs skipped. Matplotlib unavailable: {e}')
            return {k: '' for k in paths}

        DPI = 220
        BG = '#07111f'
        BG2 = '#0d1b2e'
        CARD = '#f8f6ef'
        CARD2 = '#ffffff'
        GOLD = '#d6a739'
        TEXT = '#111827'
        MUTED = '#6b7280'
        WHITE = '#f9fafb'
        RED = '#dc2626'
        BLUE = '#2563eb'
        INK = '#0f172a'

        def get_cmap(name):
            try:
                return matplotlib.colormaps[name]
            except Exception:
                return plt.cm.get_cmap(name)

        def save_clean(fig, path):
            # Do not use bbox_inches='tight' here: tight cropping was the main
            # source of title/subtitle overlap and inconsistent whitespace in the
            # previous build. Fixed-size 16:9/landscape frames keep proportions stable.
            self._add_watermark(fig)
            fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor(), edgecolor='none')
            plt.close(fig)

        def add_header(fig, title, subtitle='', badge='LUCIA'):
            # The previous build positioned badge/title/subtitle at fixed
            # figure-fraction y-values. That only happens to work when the
            # actual rendered text height matches what those fractions assumed;
            # in practice the 22pt bold title is taller than the gap left for
            # it, so the subtitle line renders overlapping the title's
            # descenders (visible as text crossed through text). Converting
            # each font size to a figure-fraction offset (points / 72 / fig
            # height in inches) keeps the stack always correctly spaced,
            # regardless of figure height (9in maps vs 9in radar, etc.).
            fig_h = fig.get_size_inches()[1]
            band_h = 0.135
            fig.patch.set_facecolor(BG)
            fig.add_artist(Rectangle((0, 1 - band_h), 1, band_h, transform=fig.transFigure,
                                     facecolor=BG2, edgecolor='none', zorder=0))
            fig.add_artist(Rectangle((0.017, 1 - band_h + 0.018), 0.006, band_h - 0.036, transform=fig.transFigure,
                                     facecolor=GOLD, edgecolor='none', zorder=1))
            badge_y = 1 - 0.045
            title_y = badge_y - (15.5 / 72.0) / fig_h
            subtitle_y = title_y - (31.0 / 72.0) / fig_h
            fig.text(0.035, badge_y, badge, color=GOLD, fontsize=13, fontweight='bold',
                     ha='left', va='top')
            fig.text(0.035, title_y, title, color=WHITE, fontsize=22, fontweight='bold',
                     ha='left', va='top')
            if subtitle:
                fig.text(0.035, subtitle_y, subtitle, color='#cbd5e1', fontsize=10.5,
                         ha='left', va='top')

        def add_card(fig, rect, face=CARD, edge='#1f2937', radius=0.018):
            patch = FancyBboxPatch((rect[0], rect[1]), rect[2], rect[3],
                                   boxstyle=f'round,pad=0.006,rounding_size={radius}',
                                   transform=fig.transFigure, facecolor=face,
                                   edgecolor=edge, linewidth=0.9, zorder=0.5)
            fig.add_artist(patch)

        def cell_color(ax, value_key, cmap_name='viridis', edge_lw=0.05, alpha=1.0):
            cmap = get_cmap(cmap_name)
            norm = Normalize(vmin=0, vmax=100)
            for cell in cells:
                val = cell.get(value_key, 0.0)
                self._plot_polygon_geom(
                    ax, cell['geom'],
                    facecolor=cmap(norm(val)),
                    edgecolor='#64748b',
                    linewidth=edge_lw,
                    alpha=alpha,
                    zorder=1
                )
            self._draw_boundary_outline(ax, boundary_geom, color=INK, linewidth=1.0)
            self._set_map_extent(ax, boundary_geom)
            ax.set_facecolor(CARD2)

        def map_axes(fig, rect, value_key, cmap_name, roads_overlay=False):
            add_card(fig, rect, face=CARD2, edge='#334155', radius=0.014)
            ax = fig.add_axes([rect[0] + 0.018, rect[1] + 0.035, rect[2] - 0.036, rect[3] - 0.055], zorder=1)
            cell_color(ax, value_key, cmap_name)
            if roads_overlay:
                for _, g in roads:
                    self._plot_line_geom(ax, g, color='#ffffff', linewidth=0.23, alpha=0.40, zorder=2)
            self._draw_scalebar(ax, boundary_geom)
            return ax

        def colorbar(fig, cmap_name, rect, label='Score'):
            cax = fig.add_axes(rect, zorder=3)
            sm = plt.cm.ScalarMappable(cmap=get_cmap(cmap_name), norm=Normalize(vmin=0, vmax=100))
            sm.set_array([])
            cb = fig.colorbar(sm, cax=cax, orientation='vertical')
            cb.set_label(label, color=WHITE, fontsize=9)
            cb.ax.tick_params(labelsize=8, colors=WHITE)
            cb.outline.set_edgecolor('#94a3b8')
            return cb

        def colorbar_h(fig, cmap_name, rect, label='Normalized score (0–100)'):
            cax = fig.add_axes(rect, zorder=3)
            sm = plt.cm.ScalarMappable(cmap=get_cmap(cmap_name), norm=Normalize(vmin=0, vmax=100))
            sm.set_array([])
            cb = fig.colorbar(sm, cax=cax, orientation='horizontal')
            cb.set_label(label, color=WHITE, fontsize=9)
            cb.ax.tick_params(labelsize=8, colors=WHITE)
            cb.outline.set_edgecolor('#94a3b8')
            return cb

        def sample_points(points, max_n=22000):
            if not points or len(points) <= max_n:
                return points or []
            step = max(1, int(math.ceil(len(points) / float(max_n))))
            return points[::step]

        mean_scores = self._mean_scores(cells)
        overall_mean = mean_scores['Legibility']

        # 1. Urban Legibility Index Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(
                fig,
                'Urban Legibility Index Map',
                f'LUCIA — mean score {overall_mean:.1f} ({self._category(overall_mean)}) | Paths · Edges · Districts · Nodes · Landmarks'
            )
            ax = map_axes(fig, [0.035, 0.075, 0.785, 0.765], 'legibility', 'viridis', roads_overlay=True)
            colorbar(fig, 'viridis', [0.845, 0.12, 0.020, 0.46], 'Urban Legibility Score')
            # compact metric card — placed above the colorbar (not beside it) so
            # the colorbar's rotated axis label can never collide with the card,
            # regardless of how far that label's text extends horizontally.
            add_card(fig, [0.895, 0.66, 0.075, 0.19], face='#111827', edge='#334155')
            fig.text(0.932, 0.805, f'{overall_mean:.1f}', color=GOLD, fontsize=24,
                     fontweight='bold', ha='center')
            fig.text(0.932, 0.770, self._category(overall_mean), color=WHITE, fontsize=9.5,
                     ha='center')
            fig.text(0.932, 0.730, 'mean\nscore', color='#cbd5e1', fontsize=8,
                     ha='center', linespacing=1.2)
            save_clean(fig, paths['png1'])
        except Exception as e:
            feedback.pushWarning(f'PNG1 failed: {e}')
            self._fallback_chart(paths['png1'], titles['png1'])

        # 2. Five Lynch Elements Composite
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Five Lynch Elements Composite',
                       'Small-multiple comparison with consistent 0–100 normalization and proportional panel spacing')
            panel_specs = [
                ('Path Clarity', 'path_score', 'Blues'),
                ('Edge Definition', 'edge_score', 'Oranges'),
                ('District Identity', 'district_score', 'Greens'),
                ('Node Strength', 'node_score', 'Purples'),
                ('Landmark Visibility', 'landmark_score', 'Reds'),
                ('Composite Legibility', 'legibility', 'viridis'),
            ]
            # manually placed panels; avoids the large blank rows caused by subplots + equal aspect
            lefts = [0.045, 0.365, 0.685]
            bottoms = [0.505, 0.155]
            w, h = 0.27, 0.30
            for i, (title, key, cmap_name) in enumerate(panel_specs):
                col = i % 3
                row = i // 3
                rect = [lefts[col], bottoms[row], w, h]
                add_card(fig, rect, face=CARD2, edge='#334155')
                fig.text(rect[0] + 0.012, rect[1] + rect[3] - 0.026, title,
                         color=TEXT, fontsize=11, fontweight='bold', ha='left', va='top')
                ax = fig.add_axes([rect[0] + 0.014, rect[1] + 0.022, rect[2] - 0.028, rect[3] - 0.062], zorder=1)
                cell_color(ax, key, cmap_name, edge_lw=0.03)
            colorbar_h(fig, 'viridis', [0.31, 0.075, 0.38, 0.016],
                       'Normalized score (0–100), same scale used for all panels')
            save_clean(fig, paths['png2'])
        except Exception as e:
            feedback.pushWarning(f'PNG2 failed: {e}')
            self._fallback_chart(paths['png2'], titles['png2'])

        # 3. Path–Node Network
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Path–Node Network',
                       'Blue = major path network | grey = detected junctions | red = top main nodes | purple = node influence zones')
            add_card(fig, [0.035, 0.075, 0.735, 0.765], face=CARD2, edge='#334155')
            ax = fig.add_axes([0.055, 0.105, 0.695, 0.705], zorder=1)
            ax.set_facecolor(CARD2)

            for cell in cells:
                self._plot_polygon_geom(ax, cell['geom'], facecolor='#f4f7fb', edgecolor='#e2e8f0',
                                        linewidth=0.04, alpha=1.0, zorder=0)

            primary_zone_cells = [c['geom'] for c in cells if float(c.get('node_score', 0.0)) >= 85.0]
            secondary_zone_cells = [c['geom'] for c in cells if 72.0 <= float(c.get('node_score', 0.0)) < 85.0]
            emerging_zone_cells = [c['geom'] for c in cells if 60.0 <= float(c.get('node_score', 0.0)) < 72.0]
            for geoms, color, alpha in [
                (emerging_zone_cells, '#c4b5fd', 0.14),
                (secondary_zone_cells, '#a78bfa', 0.18),
                (primary_zone_cells, '#8b5cf6', 0.24),
            ]:
                try:
                    if geoms:
                        zone = QgsGeometry.unaryUnion(geoms)
                        if zone and not zone.isEmpty():
                            self._plot_polygon_geom(ax, zone, facecolor=color, edgecolor='none', linewidth=0.0, alpha=alpha, zorder=1)
                except Exception:
                    for gg in geoms:
                        self._plot_polygon_geom(ax, gg, facecolor=color, edgecolor='none', linewidth=0.0, alpha=alpha, zorder=1)

            for _, g in roads:
                self._plot_line_geom(ax, g, color=BLUE, linewidth=0.42, alpha=0.48, zorder=2)

            jpts = sample_points(junction_pts, 25000)
            if jpts:
                ax.scatter([p.x() for p in jpts], [p.y() for p in jpts], s=7,
                           marker='o', color='#475569', alpha=0.42, zorder=3)

            ranked_nodes = []
            for meta, g in junctions:
                try:
                    pt = g.asPoint() if hasattr(g, 'asPoint') else g.pointOnSurface().asPoint()
                except Exception:
                    continue
                try:
                    centrality = float(meta.get('centrality', 0.0)) if isinstance(meta, dict) else float(meta['centrality'])
                except Exception:
                    centrality = 0.0
                try:
                    degree = int(meta.get('degree', 0)) if isinstance(meta, dict) else int(meta['degree'])
                except Exception:
                    degree = 0
                ranked_nodes.append((centrality, degree, pt))
            ranked_nodes.sort(key=lambda x: (x[0], x[1]), reverse=True)
            selected_nodes = []
            min_spacing = max(300.0, (float(grid_size) if grid_size else 250.0) * 2.0)
            max_nodes = 45
            for centrality, degree, pt in ranked_nodes:
                keep = True
                for _, _, spt in selected_nodes:
                    if math.hypot(pt.x() - spt.x(), pt.y() - spt.y()) < min_spacing:
                        keep = False
                        break
                if keep:
                    selected_nodes.append((centrality, degree, pt))
                    if len(selected_nodes) >= max_nodes:
                        break

            n_total = len(selected_nodes)
            n_primary = min(10, n_total)
            n_secondary = min(15, max(0, n_total - n_primary))
            primary_nodes = selected_nodes[:n_primary]
            secondary_nodes = selected_nodes[n_primary:n_primary + n_secondary]
            emerging_nodes = selected_nodes[n_primary + n_secondary:]

            def draw_node_group(nodes, size):
                if not nodes:
                    return
                ax.scatter([pt.x() for _, _, pt in nodes], [pt.y() for _, _, pt in nodes],
                           s=size, marker='o', color=RED, alpha=0.95,
                           edgecolors='white', linewidths=0.40, zorder=5)

            draw_node_group(emerging_nodes, 28)
            draw_node_group(secondary_nodes, 42)
            draw_node_group(primary_nodes, 60)

            def label_nodes(nodes, label, max_labels=3):
                for _, _, pt in nodes[:max_labels]:
                    ax.annotate(label, xy=(pt.x(), pt.y()), xytext=(5, 5), textcoords='offset points',
                                fontsize=6.8, color='#111827', ha='left', va='bottom', zorder=6,
                                bbox=dict(boxstyle='round,pad=0.18', fc='white', ec='#cbd5e1', lw=0.45, alpha=0.92))
            label_nodes(primary_nodes, 'Primary Node', max_labels=3)
            label_nodes(secondary_nodes, 'Secondary Node', max_labels=3)
            label_nodes(emerging_nodes, 'Emerging Node', max_labels=3)

            self._draw_boundary_outline(ax, boundary_geom, color=INK, linewidth=1.1)
            self._set_map_extent(ax, boundary_geom)
            self._draw_scalebar(ax, boundary_geom)

            add_card(fig, [0.795, 0.075, 0.17, 0.765], face='#111827', edge='#334155')
            fig.text(0.815, 0.815, 'NODE NETWORK\nLEGEND', color=GOLD,
                     fontsize=12.0, fontweight='bold', ha='left', va='top', linespacing=1.05)

            y = 0.692
            fig.text(0.815, y, '●', color='#475569', fontsize=13, ha='left', va='center')
            fig.text(0.842, y, 'Junctions', color=WHITE, fontsize=10.2, fontweight='bold', ha='left', va='center')
            fig.text(0.842, y-0.029, 'All detected topological junctions', color='#cbd5e1', fontsize=7.0, ha='left', va='top')
            y -= 0.105

            fig.text(0.815, y, '●', color=RED, fontsize=13, ha='left', va='center')
            fig.text(0.842, y, 'Main nodes', color=WHITE, fontsize=10.2, fontweight='bold', ha='left', va='center')
            fig.text(0.842, y-0.029, 'Top ranked junction-based nodes', color='#cbd5e1', fontsize=7.0, ha='left', va='top')
            y -= 0.105

            fig.add_artist(Rectangle((0.815, y-0.012), 0.018, 0.018,
                                     transform=fig.transFigure, facecolor='#8b5cf6',
                                     edgecolor='white', linewidth=0.35, alpha=0.28, zorder=3))
            fig.text(0.842, y, 'Purple zones', color=WHITE, fontsize=10.2, fontweight='bold', ha='left', va='center')
            fig.text(0.842, y-0.029, 'Node influence / catchment', color='#cbd5e1', fontsize=7.0, ha='left', va='top')
            y -= 0.105

            fig.text(0.815, y, 'Primary / Secondary /\nEmerging', color=WHITE, fontsize=9.0, fontweight='bold', ha='left', va='center', linespacing=1.05)
            fig.text(0.815, y-0.040, 'Labels show node hierarchy', color='#cbd5e1', fontsize=7.0, ha='left', va='top')

            fig.text(0.815, 0.245, 'NODE INSIGHT', color=GOLD,
                     fontsize=10.5, fontweight='bold', ha='left', va='top')
            fig.text(0.815, 0.214,
                     f'Main nodes shown: {n_total}\n'
                     f'Primary {len(primary_nodes)} | Secondary {len(secondary_nodes)} | Emerging {len(emerging_nodes)}',
                     color=WHITE, fontsize=7.2, ha='left', va='top', linespacing=1.28)
            fig.text(0.815, 0.154,
                     'Interpretation: red dots are the most important\n'
                     'junction-based nodes. Purple areas indicate\n'
                     'their broader spatial influence.',
                     color='#cbd5e1', fontsize=6.8, ha='left', va='top', linespacing=1.16)

            save_clean(fig, paths['png3'])
        except Exception as e:
            feedback.pushWarning(f'PNG3 failed: {e}')
            self._fallback_chart(paths['png3'], titles['png3'])

        # 4. District Identity Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'District Identity Map',
                       f'District coherence mean score {mean_scores["District"]:.1f} | land-use dominance, entropy, POI specialization, and built-form signal')
            map_axes(fig, [0.035, 0.075, 0.785, 0.765], 'district_score', 'Greens', roads_overlay=False)
            colorbar(fig, 'Greens', [0.855, 0.19, 0.022, 0.56], 'District Identity Score')
            save_clean(fig, paths['png4'])
        except Exception as e:
            feedback.pushWarning(f'PNG4 failed: {e}')
            self._fallback_chart(paths['png4'], titles['png4'])

        # 5. Edge Barrier Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Edge Barrier Map',
                       f'Edge definition mean score {mean_scores["Edge"]:.1f} | edge lines plus buffered zone of influence')
            ax = map_axes(fig, [0.035, 0.075, 0.785, 0.765], 'edge_score', 'Oranges', roads_overlay=False)
            for _, g in edges:
                self._plot_line_geom(ax, g, color='#431407', linewidth=0.9, alpha=0.88, zorder=5)
            colorbar(fig, 'Oranges', [0.855, 0.19, 0.022, 0.56], 'Edge Definition Score')
            save_clean(fig, paths['png5'])
        except Exception as e:
            feedback.pushWarning(f'PNG5 failed: {e}')
            self._fallback_chart(paths['png5'], titles['png5'])

        # 6. Landmark Visibility Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Landmark Visibility Map',
                       f'Landmark visibility mean score {mean_scores["Landmark"]:.1f} | manual landmarks and inferred tall-building orientation anchors')
            ax = map_axes(fig, [0.035, 0.075, 0.785, 0.765], 'landmark_score', 'Reds', roads_overlay=False)
            lxs, lys = [], []
            for _, g in landmarks:
                x, y = self._point_xy(g)
                if x is not None:
                    lxs.append(x)
                    lys.append(y)
            if lxs:
                ax.scatter(lxs, lys, s=26, marker='^', color='#111827', alpha=0.95,
                           edgecolors='white', linewidths=0.4, zorder=6)
            colorbar(fig, 'Reds', [0.855, 0.19, 0.022, 0.56], 'Landmark Visibility Score')
            save_clean(fig, paths['png6'])
        except Exception as e:
            feedback.pushWarning(f'PNG6 failed: {e}')
            self._fallback_chart(paths['png6'], titles['png6'])

        # 7. Radar Chart
        labels = ['Path', 'Edge', 'District', 'Node', 'Landmark']
        try:
            fig = plt.figure(figsize=(13, 9), dpi=DPI)
            add_header(fig, 'Radar Chart — Five Lynch Elements',
                       'Comparison against the moderate threshold ring (score 50)')
            add_card(fig, [0.22, 0.075, 0.56, 0.765], face=CARD2, edge='#334155')
            ax = fig.add_axes([0.255, 0.155, 0.49, 0.62], polar=True, zorder=1, facecolor=CARD2)
            values = [mean_scores[k] for k in labels]
            values_closed = values + values[:1]
            angles = (np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist() if np
                      else [i * (2 * math.pi / len(labels)) for i in range(len(labels))])
            angles_closed = angles + angles[:1]
            ax.plot(angles_closed, [50] * len(angles_closed), linewidth=1.2,
                    linestyle='--', color='#64748b', zorder=1)
            ax.plot(angles_closed, values_closed, linewidth=2.4, color=GOLD, zorder=3)
            ax.fill(angles_closed, values_closed, alpha=0.22, color=GOLD, zorder=2)
            for ang, val in zip(angles, values):
                ax.text(ang, min(100, val + 8), f'{val:.0f}', ha='center', va='center',
                        fontsize=10, fontweight='bold', color=TEXT, zorder=4)
            ax.set_ylim(0, 100)
            ax.set_xticks(angles)
            ax.set_xticklabels(labels, fontsize=11, color=TEXT)
            ax.set_yticks([20, 40, 60, 80, 100])
            ax.tick_params(colors=TEXT)
            ax.grid(color='#cbd5e1', alpha=0.75)
            fig.text(0.50, 0.092, 'Dashed ring = Moderate threshold (score 50)',
                     ha='center', fontsize=9.5, color='#cbd5e1')
            save_clean(fig, paths['png7'])
        except Exception as e:
            feedback.pushWarning(f'PNG7 failed: {e}')
            self._fallback_chart(paths['png7'], titles['png7'])

        # 8. Planning Recommendation Matrix
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Planning Recommendation Matrix',
                       f'Overall Urban Legibility Mean: {overall_mean:.1f} ({self._category(overall_mean)})')
            # summary score card
            add_card(fig, [0.035, 0.73, 0.22, 0.11], face='#111827', edge='#334155')
            fig.text(0.055, 0.805, 'OVERALL SCORE', color='#cbd5e1', fontsize=8.5, fontweight='bold')
            fig.text(0.055, 0.765, f'{overall_mean:.1f}', color=GOLD, fontsize=26, fontweight='bold')
            fig.text(0.135, 0.772, self._category(overall_mean), color=WHITE, fontsize=12, fontweight='bold')
            fig.text(0.035, 0.69, 'Priority actions are sorted by Lynch element, using each element mean score and status.',
                     color='#cbd5e1', fontsize=9.5)

            y0 = 0.58
            row_h = 0.096
            gap = 0.020
            labels_matrix = labels
            for i, theme in enumerate(labels_matrix):
                score = mean_scores[theme]
                status = self._category(score)
                rec = self._score_to_recommendation(theme, score)
                y = y0 - i * (row_h + gap)
                # row card
                add_card(fig, [0.035, y, 0.93, row_h], face='#f8fafc', edge='#334155', radius=0.012)
                # score block
                status_color = '#991b1b' if score < 40 else ('#b45309' if score < 60 else '#166534')
                fig.add_artist(FancyBboxPatch((0.050, y + 0.018), 0.075, row_h - 0.036,
                                               boxstyle='round,pad=0.004,rounding_size=0.010',
                                               transform=fig.transFigure, facecolor=status_color,
                                               edgecolor='none', zorder=2))
                fig.text(0.0875, y + row_h/2 + 0.008, f'{score:.1f}', color='white',
                         fontsize=15, fontweight='bold', ha='center', va='center')
                fig.text(0.0875, y + row_h/2 - 0.018, 'score', color='#e5e7eb',
                         fontsize=6.5, ha='center', va='center')

                fig.text(0.150, y + row_h * 0.64, theme, color=TEXT, fontsize=13,
                         fontweight='bold', ha='left', va='center')
                fig.text(0.150, y + row_h * 0.36, status, color=status_color, fontsize=9.5,
                         fontweight='bold', ha='left', va='center')
                wrapped = '\n'.join(_textwrap.wrap(rec, width=92))
                fig.text(0.285, y + row_h * 0.52, wrapped, color=TEXT, fontsize=10.5,
                         ha='left', va='center', linespacing=1.20)

            # compact footer
            fig.text(0.035, 0.055,
                     'Interpretation: scores below 40 indicate weak legibility signals; 40–60 moderate; above 60 strong and ready to be consolidated.',
                     color='#cbd5e1', fontsize=9.2)
            save_clean(fig, paths['png8'])
        except Exception as e:
            feedback.pushWarning(f'PNG8 failed: {e}')
            self._fallback_chart(paths['png8'], titles['png8'])

        # 9. Planning Recommendation Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Planning Recommendation Zone Map',
                       'Smoothed priority zones from context-gated Lynch diagnosis; pale/neutral areas mean maintain, adequate structure, or low evidence for intervention')
            add_card(fig, [0.035, 0.075, 0.735, 0.765], face=CARD2, edge='#334155')
            ax = fig.add_axes([0.055, 0.105, 0.695, 0.705], zorder=1)
            ax.set_facecolor(CARD2)

            for cell in cells:
                self._plot_polygon_geom(ax, cell['geom'], facecolor='#e5e7eb',
                                        edgecolor='#e2e8f0', linewidth=0.025,
                                        alpha=1.0, zorder=0)

            for cell in cells:
                theme = cell.get('rec_theme_smooth', cell.get('rec_theme', 'Path'))
                priority = float(cell.get('rec_priority_smooth', cell.get('rec_priority', 0.0)))
                if theme == 'Maintain' or priority < 35:
                    self._plot_polygon_geom(ax, cell['geom'], facecolor=self._rec_theme_zone_color('Maintain'),
                                            edgecolor='none', linewidth=0.0, alpha=0.45, zorder=1)
                    continue
                alpha = 0.42 + 0.30 * (priority / 100.0)
                self._plot_polygon_geom(ax, cell['geom'],
                                        facecolor=self._rec_theme_zone_color(theme),
                                        edgecolor='none', linewidth=0.0,
                                        alpha=max(0.40, min(0.72, alpha)),
                                        zorder=1)

            self._draw_boundary_outline(ax, boundary_geom, color=INK, linewidth=1.1)
            self._set_map_extent(ax, boundary_geom)
            self._draw_scalebar(ax, boundary_geom)

            add_card(fig, [0.795, 0.075, 0.17, 0.765], face='#111827', edge='#334155')
            fig.text(0.815, 0.805, 'RECOMMENDED\nCITY IMAGE ACTIONS', color=GOLD,
                     fontsize=13, fontweight='bold', ha='left', va='top', linespacing=1.1)
            legend_items = [
                ('Path', 'Clarify movement spine /\nwayfinding'),
                ('Edge', 'Treat barrier, seam,\ncrossing, waterfront'),
                ('District', 'Strengthen district\nidentity'),
                ('Node', 'Create or intensify\nactivity center'),
                ('Landmark', 'Add / highlight\norientation anchor'),
                ('Maintain', 'Maintain / low priority'),
            ]
            y = 0.690
            for theme, desc in legend_items:
                fig.add_artist(Rectangle((0.815, y-0.012), 0.018, 0.018,
                                         transform=fig.transFigure,
                                         facecolor=self._rec_theme_zone_color(theme),
                                         edgecolor='white', linewidth=0.4, zorder=3))
                fig.text(0.842, y, theme, color=WHITE, fontsize=10.0, fontweight='bold',
                         ha='left', va='center')
                fig.text(0.842, y-0.028, desc, color='#cbd5e1', fontsize=6.9,
                         ha='left', va='top', linespacing=1.12)
                y -= 0.092

            top_counts = Counter([c.get('rec_theme_smooth', c.get('rec_theme', 'Path')) for c in cells
                                  if c.get('rec_priority_smooth', c.get('rec_priority', 0.0)) >= 35
                                  and c.get('rec_theme_smooth', c.get('rec_theme', 'Path')) != 'Maintain'])
            dominant = top_counts.most_common(1)[0][0] if top_counts else 'Maintain'
            fig.text(0.815, 0.156, f'Dominant action zone: {dominant}', color=GOLD,
                     fontsize=9.8, fontweight='bold', ha='left')
            fig.text(0.815, 0.118,
                     'Legend chips use the same zone palette as the grid.\n'
                     'Darker zones indicate higher intervention priority.',
                     color='#cbd5e1', fontsize=6.9, ha='left', linespacing=1.15)
            save_clean(fig, paths['png9'])
        except Exception as e:
            feedback.pushWarning(f'PNG9 failed: {e}')
            self._fallback_chart(paths['png9'], titles['png9'])

        # 10. City Image Intervention Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'City Image Action Map',
                       'Simplified interpretation map: where the city image needs corridor, edge, district, node, or landmark intervention')
            add_card(fig, [0.035, 0.075, 0.735, 0.765], face=CARD2, edge='#334155')
            ax = fig.add_axes([0.055, 0.105, 0.695, 0.705], zorder=1)
            ax.set_facecolor(CARD2)

            def select_sparse_points(theme_name, min_priority=55.0, max_count=45, min_spacing=500.0):
                candidates = []
                for c in cells:
                    theme = c.get('rec_theme_smooth', c.get('rec_theme', 'Maintain'))
                    priority = float(c.get('rec_priority_smooth', c.get('rec_priority', 0.0)))
                    if theme != theme_name or priority < min_priority:
                        continue
                    try:
                        pt = c['centroid'].asPoint()
                    except Exception:
                        continue
                    candidates.append((priority, pt))
                candidates.sort(key=lambda x: x[0], reverse=True)
                selected = []
                for priority, pt in candidates:
                    keep = True
                    for _, spt in selected:
                        if math.hypot(pt.x() - spt.x(), pt.y() - spt.y()) < min_spacing:
                            keep = False
                            break
                    if keep:
                        selected.append((priority, pt))
                        if len(selected) >= max_count:
                            break
                return selected

            action_counts = Counter()
            action_area = defaultdict(float)
            for c in cells:
                theme = c.get('rec_theme_smooth', c.get('rec_theme', 'Maintain'))
                priority = float(c.get('rec_priority_smooth', c.get('rec_priority', 0.0)))
                if theme != 'Maintain' and priority >= 35:
                    action_counts[theme] += 1
                    action_area[theme] += float(c.get('area_ha', 0.0))
            dominant = action_counts.most_common(1)[0][0] if action_counts else 'Maintain'
            total_action_ha = sum(action_area.values()) if action_area else 0.0

            for cell in cells:
                self._plot_polygon_geom(ax, cell['geom'], facecolor='#f1f5f9',
                                        edgecolor='#e2e8f0', linewidth=0.018,
                                        alpha=1.0, zorder=0)

            for cell in cells:
                theme = cell.get('rec_theme_smooth', cell.get('rec_theme', 'Maintain'))
                priority = float(cell.get('rec_priority_smooth', cell.get('rec_priority', 0.0)))
                if theme == 'District' and priority >= 42:
                    self._plot_polygon_geom(ax, cell['geom'], facecolor=self._rec_theme_zone_color('District'),
                                            edgecolor='none', linewidth=0, alpha=0.45, zorder=1)

            path_cells = [c['geom'] for c in cells if c.get('rec_theme_smooth', c.get('rec_theme')) == 'Path'
                          and c.get('rec_priority_smooth', c.get('rec_priority', 0)) >= 42]
            path_zone = None
            try:
                path_zone = QgsGeometry.unaryUnion(path_cells) if path_cells else None
            except Exception:
                path_zone = None
            for _, g in roads:
                self._plot_line_geom(ax, g, color='#cbd5e1', linewidth=0.14, alpha=0.16, zorder=2)
                if path_zone is not None:
                    try:
                        if g.intersects(path_zone):
                            self._plot_line_geom(ax, g, color=self._rec_theme_color('Path'),
                                                 linewidth=1.00, alpha=0.90, zorder=5)
                    except Exception:
                        pass

            edge_cells = [c['geom'] for c in cells if c.get('rec_theme_smooth', c.get('rec_theme')) == 'Edge'
                          and c.get('rec_priority_smooth', c.get('rec_priority', 0)) >= 42]
            edge_zone = None
            try:
                edge_zone = QgsGeometry.unaryUnion(edge_cells) if edge_cells else None
            except Exception:
                edge_zone = None
            if edge_zone is not None:
                for _, g in edges:
                    try:
                        if g.intersects(edge_zone):
                            self._plot_line_geom(ax, g, color=self._rec_theme_color('Edge'),
                                                 linewidth=1.20, alpha=0.95, zorder=6)
                    except Exception:
                        pass

            node_pts = select_sparse_points('Node', min_priority=55.0, max_count=45, min_spacing=500.0)
            lm_pts = select_sparse_points('Landmark', min_priority=58.0, max_count=18, min_spacing=850.0)
            if node_pts:
                ax.scatter([pt.x() for _, pt in node_pts], [pt.y() for _, pt in node_pts],
                           s=38, color=self._rec_theme_color('Node'),
                           edgecolors='white', linewidths=0.40, alpha=0.92, zorder=8)
            if lm_pts:
                ax.scatter([pt.x() for _, pt in lm_pts], [pt.y() for _, pt in lm_pts],
                           s=54, marker='*', color=self._rec_theme_color('Landmark'),
                           edgecolors='white', linewidths=0.40, alpha=0.96, zorder=9)

            lxs, lys = [], []
            for _, g in landmarks:
                x, y = self._point_xy(g)
                if x is not None:
                    lxs.append(x)
                    lys.append(y)
            if lxs:
                ax.scatter(lxs, lys, s=34, marker='^', color='#111827',
                           edgecolors='white', linewidths=0.35, alpha=0.95, zorder=10)

            self._draw_boundary_outline(ax, boundary_geom, color=INK, linewidth=1.1)
            self._set_map_extent(ax, boundary_geom)
            self._draw_scalebar(ax, boundary_geom)

            add_card(fig, [0.795, 0.075, 0.17, 0.765], face='#111827', edge='#334155')
            fig.text(0.815, 0.815, 'MAP INSIGHT', color=GOLD,
                     fontsize=13, fontweight='bold', ha='left', va='top')
            if dominant == 'Maintain':
                fig.text(0.815, 0.765, 'Dominant reading:\nMaintain / low priority',
                         color=WHITE, fontsize=9.3, fontweight='bold', ha='left', va='top', linespacing=1.15)
                fig.text(0.815, 0.705, 'No strong intervention theme passes\nthe action threshold.',
                         color='#cbd5e1', fontsize=7.6, ha='left', va='top', linespacing=1.20)
            else:
                fig.text(0.815, 0.765, f'Dominant action:\n{dominant}',
                         color=WHITE, fontsize=9.3, fontweight='bold', ha='left', va='top', linespacing=1.15)
                fig.text(0.815, 0.705, f'Priority area: {total_action_ha:,.1f} ha',
                         color='#cbd5e1', fontsize=7.6, ha='left', va='top')

            y0 = 0.660
            top_items = action_counts.most_common(3)
            if top_items:
                fig.text(0.815, y0, 'Top intervention themes:', color=GOLD,
                         fontsize=8.4, fontweight='bold', ha='left', va='top')
                y0 -= 0.035
                for theme, cnt in top_items:
                    area = action_area.get(theme, 0.0)
                    fig.add_artist(Rectangle((0.815, y0-0.010), 0.014, 0.014,
                                             transform=fig.transFigure,
                                             facecolor=self._rec_theme_color(theme),
                                             edgecolor='white', linewidth=0.3, zorder=3))
                    fig.text(0.836, y0, f'{theme}: {area:,.0f} ha',
                             color='#e5e7eb', fontsize=7.6, ha='left', va='center')
                    y0 -= 0.033

            fig.text(0.815, 0.515, 'HOW TO READ', color=GOLD,
                     fontsize=10.5, fontweight='bold', ha='left', va='top')
            fig.text(0.815, 0.478,
                     'This is an action map, not a\ncomplete base map. Colored objects\nshow where one Lynch element is\nthe dominant intervention need.',
                     color='#cbd5e1', fontsize=6.9, ha='left', va='top', linespacing=1.14)

            fig.text(0.815, 0.355, 'LEGEND', color=GOLD, fontsize=10.0, fontweight='bold', ha='left', va='top')
            legend_y = 0.320
            legend_rows = [
                ('━━', self._rec_theme_color('Path'), 'Path corridor'),
                ('━━', self._rec_theme_color('Edge'), 'Edge / seam treatment'),
                ('■', self._rec_theme_zone_color('District'), 'District zone'),
                ('●', self._rec_theme_color('Node'), 'Main node'),
                ('★', self._rec_theme_color('Landmark'), 'Landmark anchor'),
            ]
            for symbol, color, label in legend_rows:
                fig.text(0.815, legend_y, symbol, color=color, fontsize=12, ha='left', va='center')
                fig.text(0.842, legend_y, label, color='#f8fafc', fontsize=7.1, ha='left', va='center')
                legend_y -= 0.033

            fig.text(0.815, 0.124,
                     'Grey = maintain / low priority.\nUse this PNG to decide which\ntype of city-image intervention\nshould be prioritized spatially.',
                     color='#cbd5e1', fontsize=6.1, ha='left', va='top', linespacing=1.10)
            save_clean(fig, paths['png10'])
        except Exception as e:
            feedback.pushWarning(f'PNG10 failed: {e}')
            self._fallback_chart(paths['png10'], titles['png10'])

        # 11. Computational City Image Map
        try:
            fig = plt.figure(figsize=(16, 9), dpi=DPI)
            add_header(fig, 'Computational City Image Map',
                       'Object-based synthesis of paths, nodes, districts, edges, and landmarks, extended with POI, occupancy, height, and NTL support')
            add_card(fig, [0.035, 0.075, 0.735, 0.765], face=CARD2, edge='#334155')
            ax = fig.add_axes([0.055, 0.105, 0.695, 0.705], zorder=1)
            ax.set_facecolor(CARD2)

            # Districts as soft cognitive regions: use district score as opacity.
            for cell in cells:
                ds = float(cell.get('district_score', 0.0))
                if ds >= 45:
                    alpha = 0.14 + 0.24 * min(1.0, (ds - 45.0) / 55.0)
                    self._plot_polygon_geom(ax, cell['geom'], facecolor='#16a34a',
                                            edgecolor='none', linewidth=0.0, alpha=alpha, zorder=1)
                else:
                    self._plot_polygon_geom(ax, cell['geom'], facecolor='#f8fafc',
                                            edgecolor='#e5e7eb', linewidth=0.018, alpha=1.0, zorder=0)

            # Paths as legible movement lines.
            road_lengths = []
            for _, g in roads:
                try:
                    road_lengths.append(g.length())
                except Exception:
                    pass
            max_len = max(road_lengths) if road_lengths else 1.0
            for _, g in roads:
                try:
                    lw = 0.25 + 1.85 * min(1.0, g.length() / max_len)
                except Exception:
                    lw = 0.45
                self._plot_line_geom(ax, g, color='#2563eb', linewidth=lw, alpha=0.70, zorder=4)

            # Edges as organising seams/boundaries.
            for _, g in edges:
                self._plot_line_geom(ax, g, color='#f97316', linewidth=1.10, alpha=0.90, zorder=5)

            # Nodes: only main junctions, filtered by centrality and spacing.
            main_nodes = self._select_main_nodes_for_cmap(
                junctions,
                max_count=int(cmap_max_main_nodes),
                min_centrality=float(cmap_node_min_centrality),
                min_spacing=float(cmap_node_min_spacing)
            )
            if main_nodes:
                ax.scatter([pt.x() for pt in main_nodes], [pt.y() for pt in main_nodes],
                           s=34, marker='o', color='#7c3aed', alpha=0.92,
                           edgecolors='white', linewidths=0.35, zorder=7)

            # Landmarks: manual landmarks + a filtered small set of inferred landmarks.
            manual_lm_pts = []
            lxs, lys = [], []
            for _, g in landmarks:
                x, y = self._point_xy(g)
                if x is not None:
                    lxs.append(x); lys.append(y)
                    manual_lm_pts.append((x, y))
            if lxs:
                ax.scatter(lxs, lys, s=68, marker='*', color='#dc2626',
                           edgecolors='white', linewidths=0.45, alpha=0.98, zorder=9)

            inferred_pts = []
            if cmap_show_inferred_landmarks:
                inferred_pts = self._select_inferred_landmarks_for_cmap(
                    cells,
                    min_score=float(cmap_inferred_landmark_min_score),
                    max_count=int(cmap_max_inferred_landmarks),
                    min_spacing=float(cmap_inferred_landmark_min_spacing)
                )
            if inferred_pts:
                ax.scatter([pt.x() for pt in inferred_pts], [pt.y() for pt in inferred_pts],
                           s=32, marker='^', color='#ef4444',
                           edgecolors='white', linewidths=0.30, alpha=0.88, zorder=8)

            self._draw_boundary_outline(ax, boundary_geom, color=INK, linewidth=1.15)
            self._set_map_extent(ax, boundary_geom)
            self._draw_scalebar(ax, boundary_geom)

            add_card(fig, [0.795, 0.075, 0.17, 0.765], face='#111827', edge='#334155')
            fig.text(0.815, 0.805, 'COMPUTATIONAL\nIMAGE ELEMENTS', color=GOLD,
                     fontsize=13, fontweight='bold', ha='left', va='top', linespacing=1.1)

            # Shape-aware legend
            fig.text(0.815, 0.730, '━━', color='#2563eb', fontsize=14, ha='left', va='center')
            fig.text(0.842, 0.730, 'Path', color=WHITE, fontsize=10.5, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.704, 'blue line / corridor', color='#cbd5e1', fontsize=7.8, ha='left', va='top')

            fig.text(0.815, 0.625, '━━', color='#f97316', fontsize=14, ha='left', va='center')
            fig.text(0.842, 0.625, 'Edge', color=WHITE, fontsize=10.5, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.599, 'orange line / seam', color='#cbd5e1', fontsize=7.8, ha='left', va='top')

            fig.add_artist(Rectangle((0.815, 0.505), 0.018, 0.018,
                                     transform=fig.transFigure, facecolor='#16a34a',
                                     edgecolor='white', linewidth=0.4, zorder=3))
            fig.text(0.842, 0.514, 'District', color=WHITE, fontsize=10.5, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.488, 'green soft region', color='#cbd5e1', fontsize=7.8, ha='left', va='top')

            fig.text(0.815, 0.409, '●', color='#7c3aed', fontsize=16, ha='left', va='center')
            fig.text(0.842, 0.409, 'Main Node', color=WHITE, fontsize=10.5, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.383, 'purple circle = major junction', color='#cbd5e1', fontsize=7.8, ha='left', va='top')

            fig.text(0.815, 0.313, '★', color='#dc2626', fontsize=15, ha='left', va='center')
            fig.text(0.842, 0.313, 'Manual Landmark', color=WHITE, fontsize=10.2, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.287, 'red star = supplied landmark point', color='#cbd5e1', fontsize=7.6, ha='left', va='top')

            fig.text(0.815, 0.225, '▲', color='#ef4444', fontsize=13, ha='left', va='center')
            fig.text(0.842, 0.225, 'Inferred Landmark', color=WHITE, fontsize=10.0, fontweight='bold', ha='left', va='center')
            fig.text(0.842, 0.199, 'red triangle = filtered inferred anchor', color='#cbd5e1', fontsize=7.4, ha='left', va='top')

            fig.text(0.815, 0.108,
                     f'Node filter: centrality ≥ {float(cmap_node_min_centrality):.2f}, max {int(cmap_max_main_nodes)}\n'
                     f'Landmark filter: score ≥ {float(cmap_inferred_landmark_min_score):.0f}, max {int(cmap_max_inferred_landmarks)}',
                     color='#cbd5e1', fontsize=7.0, ha='left', linespacing=1.22)
            save_clean(fig, paths['png11'])
        except Exception as e:
            feedback.pushWarning(f'PNG11 failed: {e}')
            self._fallback_chart(paths['png11'], titles['png11'])


        return paths

    # ---------- Main processing ----------

    def processAlgorithm(self, parameters, context, feedback):
        boundary_src = self.parameterAsSource(parameters, self.BOUNDARY, context)
        roads_src = self.parameterAsSource(parameters, self.ROADS, context)
        poi_src = self.parameterAsSource(parameters, self.POI, context)
        buildings_src = self.parameterAsSource(parameters, self.BUILDINGS, context)
        landuse_src = self.parameterAsSource(parameters, self.LANDUSE, context)
        edge_src = self.parameterAsSource(parameters, self.EDGE_LINES, context)
        ntl_raster = self.parameterAsRasterLayer(parameters, self.NTL_RASTER, context)
        transit_src = self.parameterAsSource(parameters, self.TRANSIT, context)
        landmarks_src = self.parameterAsSource(parameters, self.LANDMARKS, context)

        if boundary_src is None or roads_src is None:
            raise QgsProcessingException('Boundary and road network are required.')

        road_class_field = self.parameterAsString(parameters, self.ROAD_CLASS_FIELD, context)
        auto_edge_from_roads = self.parameterAsBool(parameters, self.AUTO_EDGE_FROM_ROADS, context)
        road_edge_class_values = self.parameterAsString(parameters, self.ROAD_EDGE_CLASS_VALUES, context)
        poi_class = self.parameterAsString(parameters, self.POI_CLASS_FIELD, context)
        height_field = self.parameterAsString(parameters, self.BUILDING_HEIGHT_FIELD, context)
        occupancy_field = self.parameterAsString(parameters, self.BUILDING_OCCUPANCY_FIELD, context)
        lu_field = self.parameterAsString(parameters, self.LANDUSE_FIELD, context)
        landmark_name_field = self.parameterAsString(parameters, self.LANDMARK_NAME_FIELD, context)
        _ = landmark_name_field  # reserved for future use

        grid_size = self.parameterAsDouble(parameters, self.GRID_SIZE, context)
        node_radius = self.parameterAsDouble(parameters, self.NODE_RADIUS, context)
        edge_buffer = self.parameterAsDouble(parameters, self.EDGE_BUFFER, context)
        landmark_radius = self.parameterAsDouble(parameters, self.LANDMARK_RADIUS, context)
        ntl_band = int(self.parameterAsInt(parameters, self.NTL_BAND, context))
        ntl_influence = self.parameterAsDouble(parameters, self.NTL_INFLUENCE, context)
        use_ntl_node = self.parameterAsBool(parameters, self.USE_NTL_NODE, context)
        use_ntl_district = self.parameterAsBool(parameters, self.USE_NTL_DISTRICT, context)
        use_ntl_landmark = self.parameterAsBool(parameters, self.USE_NTL_LANDMARK, context)
        use_occupancy_node = self.parameterAsBool(parameters, self.USE_OCCUPANCY_NODE, context)
        use_occupancy_district = self.parameterAsBool(parameters, self.USE_OCCUPANCY_DISTRICT, context)
        use_occupancy_landmark = self.parameterAsBool(parameters, self.USE_OCCUPANCY_LANDMARK, context)
        min_landmark_height = self.parameterAsDouble(parameters, self.MIN_LANDMARK_HEIGHT, context)
        cmap_show_inferred_landmarks = self.parameterAsBool(parameters, self.CMAP_SHOW_INFERRED_LANDMARKS, context)
        cmap_max_inferred_landmarks = int(self.parameterAsInt(parameters, self.CMAP_MAX_INFERRED_LANDMARKS, context))
        cmap_inferred_landmark_min_score = self.parameterAsDouble(parameters, self.CMAP_INFERRED_LANDMARK_MIN_SCORE, context)
        cmap_inferred_landmark_min_spacing = self.parameterAsDouble(parameters, self.CMAP_INFERRED_LANDMARK_MIN_SPACING, context)
        cmap_max_main_nodes = int(self.parameterAsInt(parameters, self.CMAP_MAX_MAIN_NODES, context))
        cmap_node_min_centrality = self.parameterAsDouble(parameters, self.CMAP_NODE_MIN_CENTRALITY, context)
        cmap_node_min_spacing = self.parameterAsDouble(parameters, self.CMAP_NODE_MIN_SPACING, context)
        make_png = self.parameterAsBool(parameters, self.MAKE_PNG, context)
        add_to_project = self.parameterAsBool(parameters, self.ADD_TO_PROJECT, context)
        out_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        os.makedirs(out_folder, exist_ok=True)

        # Determine target CRS using boundary centroid in original CRS.
        raw_union = self._union_boundary(boundary_src, boundary_src.sourceCrs())
        target_crs = self._local_projected_crs(boundary_src.sourceCrs(), raw_union)
        boundary_geom = self._union_boundary(boundary_src, target_crs)
        ntl_transform = None
        if ntl_raster is not None and ntl_raster.crs() != target_crs:
            ntl_transform = QgsCoordinateTransform(target_crs, ntl_raster.crs(), QgsProject.instance())

        feedback.pushInfo(f'Target analysis CRS: {target_crs.authid()}')
        feedback.pushInfo('Creating analysis grid...')
        cells = self._make_grid(boundary_geom, grid_size, feedback)
        if not cells:
            raise QgsProcessingException('No grid cells created. Check boundary geometry and CRS.')
        feedback.pushInfo(f'Grid cells inside boundary: {len(cells):,}')

        feedback.pushInfo('Loading and indexing input layers...')
        all_roads = self._collect_geoms(roads_src, target_crs, feedback)
        filtered_roads = self._filter_path_roads(all_roads, road_class_field, feedback)
        roads, roads_idx = self._build_index(filtered_roads)

        # Edge source can come from manual EDGE_LINES and/or automatically from road hierarchy.
        manual_edges = self._collect_geoms(edge_src, target_crs, feedback) if edge_src else []
        road_edges = self._filter_edge_roads(all_roads, road_class_field, road_edge_class_values, feedback) if auto_edge_from_roads else []
        combined_edges = []
        combined_edges.extend(manual_edges)
        combined_edges.extend(road_edges)
        edges, edge_idx = self._build_index(combined_edges) if combined_edges else ([], None)
        feedback.pushInfo(f'Edge candidates used: {len(edges):,} total ({len(manual_edges):,} manual + {len(road_edges):,} road-derived).')

        pois, poi_idx = self._build_index(self._collect_geoms(poi_src, target_crs, feedback)) if poi_src else ([], None)
        buildings, building_idx = self._build_index(self._collect_geoms(buildings_src, target_crs, feedback)) if buildings_src else ([], None)
        landuses, landuse_idx = self._build_index(self._collect_geoms(landuse_src, target_crs, feedback)) if landuse_src else ([], None)
        transit, transit_idx = self._build_index(self._collect_geoms(transit_src, target_crs, feedback)) if transit_src else ([], None)
        landmarks, landmark_idx = self._build_index(self._collect_geoms(landmarks_src, target_crs, feedback)) if landmarks_src else ([], None)

        # Genuine Lynch "node" detection: convergence points of the major path network,
        # not every local street segment.
        feedback.pushInfo('Detecting ranked path-network junctions (Lynch nodes)...')
        junction_ranked = self._detect_junctions_ranked(roads)
        junctions, junction_idx = self._build_index(junction_ranked) if junction_ranked else ([], None)
        junction_pts = [g.asPoint() for _, g in junction_ranked] if junction_ranked else []
        feedback.pushInfo(f'Detected {len(junction_pts):,} ranked path-network junctions.')

        # Edge zone of influence: a barrier (river/rail/etc.) affects the legibility
        # of the blocks alongside it, not only the exact strip it crosses.
        edge_buffer_zone = self._build_edge_buffer_zone(edges, edge_buffer) if edges else None

        feedback.pushInfo('Calculating raw element metrics...')
        raw_path, raw_edge, raw_district, raw_node, raw_landmark, raw_ntl = [], [], [], [], [], []

        for i, cell in enumerate(cells):
            if feedback.isCanceled():
                break
            g = cell['geom']
            centroid_pt = cell['centroid'].asPoint() if hasattr(cell['centroid'], 'asPoint') else cell['centroid']
            area_ha = cell['area'] / 10000.0 if cell['area'] else 0.0
            area_km2 = cell['area'] / 1000000.0 if cell['area'] else 0.0

            road_len, road_dominant_len = self._road_continuity_in_cell(roads_idx, roads, g)
            edge_len = self._length_in_cell(edge_idx, edges, g) if edge_idx else 0.0
            poi_count, poi_classes = self._poi_stats_in_cell(poi_idx, pois, g, poi_class) if poi_idx else (0, Counter())
            transit_count = self._count_in_cell(transit_idx, transit, g) if transit_idx else 0
            b_count, b_area, b_hmax, _, b_homogeneity, occ_dom, occ_dom_pct, occ_entropy, occ_classes, occ_activity, occ_res_share, occ_identity = self._building_stats_in_cell(building_idx, buildings, g, height_field, occupancy_field) if building_idx else (0, 0.0, 0.0, 0, 0.0, 'No data', 0.0, 0.0, 0, 0.0, 0.0, 0.0)
            building_coverage = b_area / max(cell['area'], 1e-9)
            occ_activity_eff = occ_activity if (occupancy_field and use_occupancy_node) else 0.0
            occ_identity_eff = occ_identity if (occupancy_field and use_occupancy_district) else 0.0
            occ_res_share_eff = occ_res_share if (occupancy_field and use_occupancy_district) else 0.0
            lu_dom, lu_dominance, lu_entropy, lu_n = self._landuse_stats(landuse_idx, landuses, g, lu_field) if landuse_idx else ('No data', 0.0, 0.0, 0)
            lm_count = self._count_in_cell(landmark_idx, landmarks, g) if landmark_idx else 0
            inferred_tall = 1 if b_hmax >= min_landmark_height and min_landmark_height > 0 else 0
            lm_near = self._near_weighted(landmark_idx, landmarks, centroid_pt, landmark_radius) if landmark_idx else 0.0
            ntl_raw = self._sample_raster_at_point(ntl_raster, centroid_pt, ntl_band, ntl_transform) if ntl_raster is not None else None
            ntl_raw = 0.0 if ntl_raw is None else ntl_raw

            # --- Path: density tempered by continuity (one long through-road
            # reads as more legible than the same length split into fragments). ---
            path_density = road_len / max(area_km2, 1e-9)
            continuity_ratio = (road_dominant_len / road_len) if road_len > 1e-9 else 0.0
            path_metric = path_density * (0.5 + 0.5 * continuity_ratio)

            # --- Edge: direct line-in-cell density plus the buffered zone of
            # influence (now actually using EDGE_BUFFER, previously unused). ---
            edge_density = edge_len / max(area_km2, 1e-9)
            edge_buffer_frac = 0.0
            if edge_buffer_zone is not None:
                try:
                    if g.intersects(edge_buffer_zone):
                        edge_buffer_frac = g.intersection(edge_buffer_zone).area() / max(cell['area'], 1e-9)
                except Exception:
                    edge_buffer_frac = 0.0
            edge_metric = edge_density + 40.0 * edge_buffer_frac
            edge_context = 1.0 if edge_len > 0 else min(1.0, edge_buffer_frac)

            # --- Node: junctions + transit + activity concentration within the
            # node influence radius (now actually using NODE_RADIUS), decoupled
            # from raw road length so it no longer duplicates the Path signal. ---
            junction_near = self._near_weighted_attr(junction_idx, junctions, centroid_pt, node_radius, 'centrality', 1.0) if junction_idx else 0.0
            poi_near = self._near_weighted(poi_idx, pois, centroid_pt, node_radius) if poi_idx else 0.0
            transit_near = self._near_weighted(transit_idx, transit, centroid_pt, node_radius) if transit_idx else 0.0
            node_metric = (junction_near * 3.0) + (transit_near * 2.5) + (poi_near * 1.0) + (occ_activity_eff * 3.0)

            poi_specialization = 0.0
            if poi_count > 0 and poi_classes:
                poi_specialization = max(poi_classes.values()) / max(poi_count, 1)
            # --- District: thematic continuity. Land-use entropy now actually
            # contributes (it was previously computed and discarded); footprint-size
            # homogeneity replaces raw building coverage as the no-landuse fallback
            # signal, since coverage alone says nothing about character coherence. ---
            if landuse_idx:
                district_components = [
                    (0.35, lu_dominance),
                    (0.12, (1.0 - lu_entropy)),
                    (0.17, poi_specialization),
                    (0.15, min(1.0, building_coverage * 2.0)),
                    (0.10, b_homogeneity),
                ]
                if occupancy_field and use_occupancy_district:
                    district_components.append((0.11, occ_identity_eff))
                w_total = sum(w for w, _ in district_components) or 1.0
                district_metric = (sum(w * v for w, v in district_components) / w_total) * 100.0
            else:
                district_components = [
                    (0.30, poi_specialization),
                    (0.22, min(1.0, building_coverage * 2.0)),
                    (0.23, b_homogeneity),
                ]
                if occupancy_field and use_occupancy_district:
                    district_components.append((0.25, occ_identity_eff))
                w_total = sum(w for w, _ in district_components) or 1.0
                district_metric = (sum(w * v for w, v in district_components) / w_total) * 100.0

            # Landmark follows a visual-structural-pragmatic logic:
            # visual = manual landmarks + height prominence;
            # pragmatic/cognitive = POI specialization, occupancy activity/function;
            # dynamic salience = optional NTL support for night-time orientation need.
            ntl_support_raw = 0.0
            if ntl_raster is not None and use_ntl_landmark:
                try:
                    ntl_support_raw = min(2.0, max(0.0, ntl_raw) / 10.0)
                except Exception:
                    ntl_support_raw = 0.0
            landmark_metric = (
                (lm_count * 2.5)
                + (lm_near * 0.75)
                + (inferred_tall * 2.0)
                + (b_hmax / max(min_landmark_height, 1.0) if min_landmark_height > 0 else 0)
                + (poi_specialization * 1.0)
                + ((occ_activity_eff if use_occupancy_landmark else 0.0) * 2.0)
                + ntl_support_raw
            )

            cell.update({
                'area_ha': area_ha,
                'road_m': road_len,
                'edge_m': edge_len,
                'poi_n': poi_count,
                'transit_n': transit_count,
                'bldg_n': b_count,
                'bldg_cov': building_coverage,
                'height_max': b_hmax,
                'occ_dom': occ_dom,
                'occ_dom_pct': occ_dom_pct * 100.0,
                'occ_entropy': occ_entropy,
                'occ_classes': occ_classes,
                'occ_activity': occ_activity,
                'occ_res_share': occ_res_share,
                'occ_identity': occ_identity,
                'occ_activity_eff': occ_activity_eff,
                'occ_res_share_eff': occ_res_share_eff,
                'occ_identity_eff': occ_identity_eff,
                'lu_dom': lu_dom,
                'lu_dom_pct': lu_dominance * 100.0,
                'lu_entropy': lu_entropy,
                'lu_classes': lu_n,
                'lm_n': lm_count,
                'lm_near': lm_near,
                'junction_near': junction_near,
                'continuity_ratio': continuity_ratio,
                'ntl_raw': ntl_raw,
                'path_raw': path_metric,
                'edge_raw': edge_metric,
                'edge_context': edge_context,
                'district_raw': district_metric,
                'node_raw': node_metric,
                'landmark_raw': landmark_metric,
            })
            raw_path.append(path_metric)
            raw_edge.append(edge_metric)
            raw_district.append(district_metric)
            raw_node.append(node_metric)
            raw_landmark.append(landmark_metric)
            raw_ntl.append(ntl_raw)
            if i % 250 == 0:
                feedback.setProgress(30 + int(45 * i / max(len(cells), 1)))

        feedback.pushInfo('Normalizing scores...')
        path_scores = self._pct_norm(raw_path)
        edge_scores = self._pct_norm(raw_edge)
        district_scores = self._pct_norm(raw_district)
        node_scores = self._pct_norm(raw_node)
        landmark_scores = self._pct_norm(raw_landmark)
        ntl_scores = self._pct_norm(raw_ntl) if ntl_raster is not None else [0.0 for _ in cells]

        weights = {
            'path': self.parameterAsDouble(parameters, self.W_PATH, context),
            'edge': self.parameterAsDouble(parameters, self.W_EDGE, context),
            'district': self.parameterAsDouble(parameters, self.W_DISTRICT, context),
            'node': self.parameterAsDouble(parameters, self.W_NODE, context),
            'landmark': self.parameterAsDouble(parameters, self.W_LANDMARK, context),
        }
        wsum = sum(weights.values())
        if wsum <= 0:
            raise QgsProcessingException('At least one element weight must be greater than zero.')

        for i, cell in enumerate(cells):
            ps, es, ds, ns, ls = path_scores[i], edge_scores[i], district_scores[i], node_scores[i], landmark_scores[i]
            nts = ntl_scores[i] if ntl_scores else 0.0

            # Optional NTL adjustment: night light supports the reading of night activity,
            # emerging centers, and mixed urban intensity. It strengthens Node and District
            # signals only, so the five Lynch elements remain conceptually intact.
            if ntl_raster is not None and ntl_influence > 0:
                infl = max(0.0, min(1.0, ntl_influence))
                if use_ntl_node:
                    ns = (1.0 - infl) * ns + infl * nts
                if use_ntl_district:
                    ds = (1.0 - (infl * 0.55)) * ds + (infl * 0.55) * nts

            leg = (weights['path'] * ps + weights['edge'] * es + weights['district'] * ds + weights['node'] * ns + weights['landmark'] * ls) / wsum
            rec_theme, rec_priority, rec_text = self._cell_recommendation_v6(cell, ps, es, ds, ns, ls, nts, leg, use_ntl_node, use_ntl_district, use_ntl_landmark, use_occupancy_node, use_occupancy_district, use_occupancy_landmark)
            cell.update({
                'path_score': ps,
                'edge_score': es,
                'district_score': ds,
                'node_score': ns,
                'landmark_score': ls,
                'ntl_score': nts,
                'legibility': leg,
                'category': self._category(leg),
                'rec_theme': rec_theme,
                'rec_priority': rec_priority,
                'rec_text': rec_text,
            })

        self._smooth_recommendation_themes(cells, grid_size)

        # Create output vector layers in memory
        grid_fields = QgsFields()
        for name, typ in [
            ('cid', QVariant.Int), ('area_ha', QVariant.Double), ('path_s', QVariant.Double), ('edge_s', QVariant.Double),
            ('district_s', QVariant.Double), ('node_s', QVariant.Double), ('landmark_s', QVariant.Double),
            ('legibility', QVariant.Double), ('category', QVariant.String), ('road_m', QVariant.Double),
            ('edge_m', QVariant.Double), ('poi_n', QVariant.Int), ('transit_n', QVariant.Int), ('bldg_n', QVariant.Int),
            ('bldg_cov', QVariant.Double), ('height_max', QVariant.Double), ('occ_dom', QVariant.String),
            ('occ_dom_pc', QVariant.Double), ('occ_entropy', QVariant.Double), ('occ_classes', QVariant.Int),
            ('occ_act', QVariant.Double), ('occ_res', QVariant.Double), ('occ_ident', QVariant.Double),
            ('occ_act_eff', QVariant.Double), ('occ_res_eff', QVariant.Double), ('occ_id_eff', QVariant.Double), ('lu_dom', QVariant.String),
            ('lu_dom_pct', QVariant.Double), ('lu_entropy', QVariant.Double), ('lu_classes', QVariant.Int),
            ('lm_n', QVariant.Int), ('lm_near', QVariant.Double), ('junction_n', QVariant.Double),
            ('continuity', QVariant.Double), ('ntl_raw', QVariant.Double), ('ntl_s', QVariant.Double),
            ('rec_theme', QVariant.String), ('rec_priority', QVariant.Double), ('rec_theme_s', QVariant.String),
            ('rec_prio_s', QVariant.Double), ('rec_text', QVariant.String)
        ]:
            grid_fields.append(QgsField(name, typ))

        grid_layer = self._memory_layer('MultiPolygon', target_crs, grid_fields, 'lucia_grid')
        grid_dp = grid_layer.dataProvider()
        grid_features = []
        for cell in cells:
            feat = QgsFeature(grid_fields)
            geom = QgsGeometry(cell['geom'])
            if QgsWkbTypes.isSingleType(geom.wkbType()):
                geom.convertToMultiType()
            feat.setGeometry(geom)
            feat.setAttributes([
                cell['id'], cell['area_ha'], cell['path_score'], cell['edge_score'], cell['district_score'],
                cell['node_score'], cell['landmark_score'], cell['legibility'], cell['category'], cell['road_m'],
                cell['edge_m'], cell['poi_n'], cell['transit_n'], cell['bldg_n'], cell['bldg_cov'], cell['height_max'],
                cell.get('occ_dom', 'No data')[:250], cell.get('occ_dom_pct', 0.0), cell.get('occ_entropy', 0.0),
                cell.get('occ_classes', 0), cell.get('occ_activity', 0.0), cell.get('occ_res_share', 0.0), cell.get('occ_identity', 0.0),
                cell.get('occ_activity_eff', 0.0), cell.get('occ_res_share_eff', 0.0), cell.get('occ_identity_eff', 0.0),
                cell['lu_dom'][:250], cell['lu_dom_pct'], cell['lu_entropy'], cell['lu_classes'], cell['lm_n'], cell['lm_near'],
                cell.get('junction_near', 0.0), cell.get('continuity_ratio', 0.0), cell.get('ntl_raw', 0.0),
                cell.get('ntl_score', 0.0), cell.get('rec_theme', '')[:80], cell.get('rec_priority', 0.0),
                cell.get('rec_theme_smooth', cell.get('rec_theme', ''))[:80], cell.get('rec_priority_smooth', cell.get('rec_priority', 0.0)),
                cell.get('rec_text', '')[:250]
            ])
            grid_features.append(feat)
        grid_dp.addFeatures(grid_features)
        grid_layer.updateExtents()

        node_fields = QgsFields()
        for name, typ in [('nid', QVariant.Int), ('node_s', QVariant.Double), ('legibility', QVariant.Double), ('poi_n', QVariant.Int), ('transit_n', QVariant.Int), ('lu_dom', QVariant.String), ('category', QVariant.String)]:
            node_fields.append(QgsField(name, typ))
        node_layer = self._memory_layer('Point', target_crs, node_fields, 'lucia_node_hotspots')
        node_dp = node_layer.dataProvider()
        node_features = []
        hotspot_points = []
        nid = 1
        threshold = 75.0
        for cell in cells:
            if cell['node_score'] >= threshold:
                nf = QgsFeature(node_fields)
                centroid_geom = QgsGeometry(cell['centroid'])
                nf.setGeometry(centroid_geom)
                nf.setAttributes([nid, cell['node_score'], cell['legibility'], cell['poi_n'], cell['transit_n'], cell['lu_dom'][:250], cell['category']])
                node_features.append(nf)
                hotspot_points.append(centroid_geom.asPoint())
                nid += 1
        node_dp.addFeatures(node_features)
        node_layer.updateExtents()

        # Write all core files into one folder
        grid_gpkg = os.path.join(out_folder, 'lucia_grid.gpkg')
        nodes_gpkg = os.path.join(out_folder, 'lucia_node_hotspots.gpkg')
        summary_csv = os.path.join(out_folder, 'lucia_summary.csv')
        manifest_json = os.path.join(out_folder, 'lucia_manifest.json')

        self._write_layer_to_gpkg(grid_layer, grid_gpkg, 'lucia_grid')
        self._write_layer_to_gpkg(node_layer, nodes_gpkg, 'lucia_node_hotspots')

        if add_to_project:
            try:
                QgsProject.instance().addMapLayer(grid_layer)
                QgsProject.instance().addMapLayer(node_layer)
            except Exception:
                pass

        means = {
            'Path Clarity mean': statistics.mean([c['path_score'] for c in cells]),
            'Edge Definition mean': statistics.mean([c['edge_score'] for c in cells]),
            'District Identity mean': statistics.mean([c['district_score'] for c in cells]),
            'Node Strength mean': statistics.mean([c['node_score'] for c in cells]),
            'Landmark Visibility mean': statistics.mean([c['landmark_score'] for c in cells]),
            'Urban Legibility mean': statistics.mean([c['legibility'] for c in cells]),
            'Urban Legibility median': statistics.median([c['legibility'] for c in cells]),
            'Grid cells': len(cells),
            'Detected node hotspots': nid - 1,
            'Analysis CRS': target_crs.authid(),
            'Nighttime Light input': 'Yes' if ntl_raster is not None else 'No',
            'Nighttime Light influence': ntl_influence if ntl_raster is not None else 0.0,
            'Use NTL in Node Strength': 'Yes' if use_ntl_node else 'No',
            'Use NTL in District Identity': 'Yes' if use_ntl_district else 'No',
            'Use NTL in Landmark strategic need': 'Yes' if use_ntl_landmark else 'No',
            'Building occupancy input': 'Yes' if occupancy_field else 'No',
            'Use occupancy in Node Strength': 'Yes' if use_occupancy_node else 'No',
            'Use occupancy in District Identity': 'Yes' if use_occupancy_district else 'No',
            'Use occupancy in Landmark strategic need': 'Yes' if use_occupancy_landmark else 'No',
            'Reference integration': 'Filomena-Verstegen-Manley computational Image of the City concepts integrated with LUCIA planning logic',
            'Automatic road-derived edges': 'Yes' if auto_edge_from_roads else 'No',
            'Road classes treated as edges': road_edge_class_values,
            'Road classes treated as paths': 'primary, primary_link, secondary, secondary_link, tertiary, tertiary_link, trunk, trunk_link',
            'Manual edge features': len(manual_edges),
            'Road-derived edge features': len(road_edges),
            'Total edge candidates': len(edges),
            'Computational map main nodes max': cmap_max_main_nodes,
            'Computational map node min centrality': cmap_node_min_centrality,
            'Computational map node min spacing (m)': cmap_node_min_spacing,
            'Computational map inferred landmarks shown': 'Yes' if cmap_show_inferred_landmarks else 'No',
            'Computational map inferred landmarks max': cmap_max_inferred_landmarks,
            'Computational map inferred landmark min score': cmap_inferred_landmark_min_score,
            'Computational map inferred landmark min spacing (m)': cmap_inferred_landmark_min_spacing,
            'Mean occupancy activity share': statistics.mean([c.get('occ_activity', 0.0) for c in cells]) if cells else 0.0,
            'Mean residential share': statistics.mean([c.get('occ_res_share', 0.0) for c in cells]) if cells else 0.0,
        }
        summary_rows = []
        for k, v in means.items():
            summary_rows.append((k, f'{v:.3f}' if isinstance(v, float) else v))
        cat_counts = Counter([c['category'] for c in cells])
        for cat in ['Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong']:
            summary_rows.append((f'Cells: {cat}', cat_counts.get(cat, 0)))
        self._write_csv(summary_csv, summary_rows)

        pngs = {f'png{i}': '' for i in range(1, 9)}
        if make_png:
            pngs = self._create_png_outputs(
                out_folder, cells, boundary_geom, roads, edges, landmarks, junctions, junction_pts, hotspot_points, grid_size, feedback,
                cmap_show_inferred_landmarks, cmap_max_inferred_landmarks, cmap_inferred_landmark_min_score,
                cmap_inferred_landmark_min_spacing, cmap_max_main_nodes, cmap_node_min_centrality, cmap_node_min_spacing
            )

        # Extra deliverables in the same output folder: QGIS styles and HTML report.
        grid_qml = os.path.join(out_folder, 'lucia_grid_legibility_style.qml')
        node_qml = os.path.join(out_folder, 'lucia_node_hotspot_style.qml')
        grid_qml_text = '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>\n<qgis version="3.40" styleCategories="AllStyleCategories">\n  <renderer-v2 type="graduatedSymbol" attr="legibility" graduatedMethod="GraduatedColor">\n    <ranges><range lower="0" upper="20" symbol="0" label="Very Weak 0-20"/><range lower="20" upper="40" symbol="1" label="Weak 20-40"/><range lower="40" upper="60" symbol="2" label="Moderate 40-60"/><range lower="60" upper="80" symbol="3" label="Strong 60-80"/><range lower="80" upper="100" symbol="4" label="Very Strong 80-100"/></ranges>\n    <symbols><symbol alpha="0.88" type="fill" name="0"><layer class="SimpleFill"><prop k="color" v="68,1,84,225"/><prop k="outline_width" v="0.08"/></layer></symbol><symbol alpha="0.88" type="fill" name="1"><layer class="SimpleFill"><prop k="color" v="59,82,139,225"/><prop k="outline_width" v="0.08"/></layer></symbol><symbol alpha="0.88" type="fill" name="2"><layer class="SimpleFill"><prop k="color" v="33,145,140,225"/><prop k="outline_width" v="0.08"/></layer></symbol><symbol alpha="0.88" type="fill" name="3"><layer class="SimpleFill"><prop k="color" v="94,201,98,225"/><prop k="outline_width" v="0.08"/></layer></symbol><symbol alpha="0.88" type="fill" name="4"><layer class="SimpleFill"><prop k="color" v="253,231,37,225"/><prop k="outline_width" v="0.08"/></layer></symbol></symbols>\n  </renderer-v2>\n</qgis>\n'
        node_qml_text = '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>\n<qgis version="3.40" styleCategories="AllStyleCategories"><renderer-v2 type="singleSymbol"><symbols><symbol alpha="1" type="marker" name="0"><layer class="SimpleMarker"><prop k="name" v="circle"/><prop k="color" v="255,196,0,255"/><prop k="outline_color" v="60,30,0,255"/><prop k="size" v="3.2"/></layer></symbol></symbols></renderer-v2></qgis>\n'
        with open(grid_qml, 'w', encoding='utf-8') as f:
            f.write(grid_qml_text)
        with open(node_qml, 'w', encoding='utf-8') as f:
            f.write(node_qml_text)
        try:
            grid_layer.loadNamedStyle(grid_qml)
            node_layer.loadNamedStyle(node_qml)
        except Exception:
            pass

        html_report = os.path.join(out_folder, 'lucia_report.html')
        def _esc(v):
            return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        metric_rows = ''.join([f'<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>' for k, v in means.items()])
        class_rows = ''.join([f'<tr><td>{_esc(cat)}</td><td>{cat_counts.get(cat, 0)}</td></tr>' for cat in ['Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong']])
        figure_cards = ''
        for title, key in [('Urban Legibility Index Map','png1'),('Five Lynch Elements Composite','png2'),('Path-Node Network','png3'),('District Identity Map','png4'),('Edge Barrier Map','png5'),('Landmark Visibility Map','png6'),('Radar Chart of the Five Elements','png7'),('Planning Recommendation Matrix','png8'),('Planning Recommendation Zone Map','png9'),('City Image Action Map','png10'),('Computational City Image Map','png11')]:
            p_img = pngs.get(key, '')
            if p_img:
                figure_cards += f'<section class="figure-card"><h2>{_esc(title)}</h2><img src="{_esc(os.path.basename(p_img))}"></section>'
        html = f'''<!doctype html><html><head><meta charset="utf-8"><title>LUCIA Report</title><style>body{{margin:0;background:#0b1020;color:#f4f1e8;font-family:Arial,Helvetica,sans-serif;line-height:1.5}}header{{padding:42px 54px 28px;background:linear-gradient(135deg,#08111f,#14233f 55%,#1b1305);border-bottom:1px solid rgba(245,197,66,.35)}}h1{{margin:0;font-size:34px}}.subtitle{{color:#f5c542;margin-top:8px}}main{{padding:28px 54px 54px;max-width:1320px;margin:auto}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:22px;margin-bottom:26px}}.panel,.figure-card{{background:#111a2e;border:1px solid rgba(245,197,66,.28);border-radius:16px;padding:20px;box-shadow:0 12px 34px rgba(0,0,0,.28)}}h2{{margin:0 0 14px;color:#f5c542;font-size:18px}}table{{width:100%;border-collapse:collapse;font-size:13px}}td{{padding:9px 8px;border-bottom:1px solid rgba(255,255,255,.10);vertical-align:top}}a{{color:#f5c542}}img{{width:100%;height:auto;display:block;border-radius:12px;background:#fff}}.figure-card{{margin-bottom:26px}}</style></head><body><header><h1>LUCIA — Lynch Urban Computational Image Analyzer</h1><div class="subtitle">Urban Legibility, Imageability, and Cognitive Structure Intelligence</div></header><main><div class="grid"><section class="panel"><h2>Summary Metrics</h2><table>{metric_rows}</table></section><section class="panel"><h2>Legibility Classes</h2><table>{class_rows}</table></section><section class="panel"><h2>Output Files</h2><p><a href="{_esc(os.path.basename(grid_gpkg))}">Urban Legibility Grid</a></p><p><a href="{_esc(os.path.basename(nodes_gpkg))}">Detected Node Hotspots</a></p><p><a href="{_esc(os.path.basename(summary_csv))}">Summary CSV</a></p></section></div>{figure_cards}</main></body></html>'''
        with open(html_report, 'w', encoding='utf-8') as f:
            f.write(html)

        manifest = {
            'tool': 'LUCIA — Lynch Urban Computational Image Analyzer | Premium Layout Build v7.5.4',
            'analysis_crs': target_crs.authid(),
            'output_folder': out_folder,
            'options': {
                'use_ntl_node': use_ntl_node,
                'use_ntl_district': use_ntl_district,
                'use_ntl_landmark': use_ntl_landmark,
                'use_occupancy_node': use_occupancy_node,
                'use_occupancy_district': use_occupancy_district,
                'use_occupancy_landmark': use_occupancy_landmark,
                'auto_edge_from_roads': auto_edge_from_roads,
                'road_edge_class_values': road_edge_class_values,
                'manual_edge_features': len(manual_edges),
                'road_derived_edge_features': len(road_edges),
            },
            'files': {
                'grid_gpkg': grid_gpkg,
                'nodes_gpkg': nodes_gpkg,
                'summary_csv': summary_csv,
                'html_report': html_report,
                'grid_qml_style': grid_qml,
                'node_qml_style': node_qml,
                'png_1_urban_legibility_index_map': pngs.get('png1', ''),
                'png_2_five_lynch_elements_composite': pngs.get('png2', ''),
                'png_3_path_node_network': pngs.get('png3', ''),
                'png_4_district_identity_map': pngs.get('png4', ''),
                'png_5_edge_barrier_map': pngs.get('png5', ''),
                'png_6_landmark_visibility_map': pngs.get('png6', ''),
                'png_7_radar_chart_five_elements': pngs.get('png7', ''),
                'png_8_planning_recommendation_matrix': pngs.get('png8', ''),
                'png_9_planning_recommendation_zone_map': pngs.get('png9', ''),
                'png_10_city_image_intervention_map': pngs.get('png10', ''),
                'png_11_computational_city_image_map': pngs.get('png11', ''),
            },
        }
        with open(manifest_json, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        feedback.pushInfo('LUCIA completed. All deliverables were written into one output folder.')
        self._add_file_link(feedback, 'OPEN LUCIA OUTPUT FOLDER', out_folder)

        return {
            self.OUTPUT_FOLDER_PATH: out_folder,
        }