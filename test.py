import math
import osmnx as ox
import utm
import rhino3dm as rg
import momepy
from collections import Counter
import pandas as pd
import json
import requests

#DEM
import numpy as np
import rasterio
from pyproj import Proj, transform
import os



#@title Play function
#@markdown Function for HOPS
def getEdges(place_point,distancia):
  # 01. GET POINT PLACE AND BBOX
    # place=place_name
    # geocoder_json=geocoder.osm(place,maxRows=1)
    # lat1=geocoder_json.json['lat']
    # lng1=geocoder_json.json['lng']
    point = place_point
    new_point = point.replace(" ", "")
    split_point = new_point.split(",")
    lat1, lng1  = split_point
    lat1 = float(lat1)
    lng1 = float(lng1)

    point=(lat1,lng1)
    dist=int(distancia)
    miles = dist*0.000621371192
    class BoundingBox(object):
        def __init__(self, *args, **kwargs):
            self.lat_min = None
            self.lon_min = None
            self.lat_max = None
            self.lon_max = None

    def get_bounding_box(latitude_in_degrees, longitude_in_degrees, half_side_in_miles):
        assert half_side_in_miles > 0
        assert latitude_in_degrees >= -90.0 and latitude_in_degrees  <= 90.0
        assert longitude_in_degrees >= -180.0 and longitude_in_degrees <= 180.0

        half_side_in_km = half_side_in_miles * 1.609344
        lat = math.radians(latitude_in_degrees)
        lon = math.radians(longitude_in_degrees)

        radius  = 6371
        # Radius of the parallel at given latitude
        parallel_radius = radius*math.cos(lat)

        lat_min = lat - half_side_in_km/radius
        lat_max = lat + half_side_in_km/radius
        lon_min = lon - half_side_in_km/parallel_radius
        lon_max = lon + half_side_in_km/parallel_radius
        rad2deg = math.degrees

        box = BoundingBox()
        box.lat_min = rad2deg(lat_min)
        box.lon_min = rad2deg(lon_min)
        box.lat_max = rad2deg(lat_max)
        box.lon_max = rad2deg(lon_max)

        return (box.lon_min, box.lat_min, box.lon_max, box.lat_max )
    
    bounds = get_bounding_box(lat1,lng1,miles)
    west, south, east, north = bounds

    #GRAPH
    # G = ox.graph_from_place(place_name, network_type='walk', simplify=True) #other network types: drive, bike, drive_service, all, all_private
    G = ox.graph_from_bbox(north, south, east, west, network_type='drive',simplify=True)
    G_projected = ox.projection.project_graph(G)

    hwy_speeds = {"residential": 35, "secondary": 50, "tertiary": 60}
    G_projected = ox.add_edge_speeds(G_projected, hwy_speeds)

    # calculate travel time (seconds) for all edges
    G_projected = ox.add_edge_travel_times(G_projected)

    # see mean speed/time values by road type
    gdf_proj_streets = ox.graph_to_gdfs(G_projected, nodes=False)
    gdf_proj_streets["highway"] = gdf_proj_streets["highway"].astype(str)
    gdf_proj_streets.groupby("highway")[["length", "speed_kph", "travel_time"]].mean().round(1)

    # STREETS
    # nodes, gdf_proj_streets = ox.graph_to_gdfs(G_projected)
    # streets_graph = ox.graph_from_bbox(north, south, east, west, network_type='drive')
    # streets_graph = ox.projection.project_graph(streets_graph)

    # streets_graph = ox.speed.add_edge_speeds(streets_graph)
    # streets_graph = ox.speed.add_edge_travel_times(streets_graph)
    # gdf_proj_streets = ox.graph_to_gdfs(streets_graph, nodes=False, edges=True, node_geometry=False, fill_edge_geometry=True)

    ## Reproject to a projected crs (meters)
    utm_zone= utm.from_latlon(lat1, lng1)
    EPSG=32700-round((45+lat1)/90)*100+round((183+lng1)/6)
    crs = EPSG

    multi_line = gdf_proj_streets.geometry.values

    streets = []
    for i in multi_line:
        x,y = i.coords.xy
        x  = x.tolist()
        y  = y.tolist()
        pts = []
        for a,b in zip(x,y):
            p = rg.Point3d( float(a), float(b), 0 )
            pts.append(p)
        poly = rg.Polyline(pts).ToPolylineCurve()
        streets.append(poly)

    #BUILDINGS
    tag_building = {"building": True}
    gdf_building = ox.geometries.geometries_from_bbox(north, south, east, west, tag_building)
    buildings_gdf = ox.projection.project_gdf(gdf_building)
    buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(['Polygon', 'MultiPolygon'])]
    buildings_gdf = buildings_gdf.explode()
    buildings_gdf.reset_index(inplace=True, drop=True)

    # multi_building = buildings_gdf.geometry.values
    # buildings = []
    # for i in multi_building:
    #     x,y = i.exterior.coords.xy
    #     x  = x.tolist()
    #     y  = y.tolist()
    #     pts = []
    #     for a,b in zip(x,y):
    #         p = rg.Point3d( float(a), float(b), 0 )
    #         pts.append(p)
    #     poly_buildings = rg.Polyline(pts).ToPolylineCurve()
    #     buildings.append(poly_buildings)

    #MOMEPY
    street_prof = momepy.StreetProfile(gdf_proj_streets, buildings_gdf)
    ## WIDTHs
    gdf_proj_streets['widths'] = street_prof.w
    array_width = gdf_proj_streets.widths.values
    widths = array_width.tolist()

    ## WIDTH_deviations
    gdf_proj_streets['width_deviations'] = street_prof.wd
    array_width_deviations = gdf_proj_streets.width_deviations.values
    width_deviations = array_width_deviations.tolist()

    ## OPENNESS
    gdf_proj_streets['openness'] = street_prof.o
    array_openness= gdf_proj_streets.openness.values
    openness = array_openness.tolist()

    primal = momepy.gdf_to_nx(gdf_proj_streets, approach='primal')

    #Closeness centrality could be simplified as average distance to every other node from each node
    #Local closeness
    # #To measure local closeness_centrality we need to specify radius (how far we should go from each node). We
    # can use topological distance (e.g. 5 steps, then radius=5) or metric distance (e.g. 400 metres) - then radius=400 and
    # distance= lenght of each segment saved as a parameter of each edge. By default, momepy saves length as mm_len.
    # Weight parameter is used for centrality calculation. Again, we can use metric weight (using the same attribute as
    # above) or no weight (weight=None) at all. Or any other attribute we wish.
    primal = momepy.closeness_centrality(primal, radius=40, name='closeness400',distance='mm_len', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness400')

    # Global closeness
    # Global closeness centrality is a bit simpler as we do not have to specify radius and distance, the rest remains the same.
    primal = momepy.closeness_centrality(primal, name='closeness_global', weight='mm_len')
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'closeness_global')

    # Betweenness
    # Betweenness centrality measures the importance of each node or edge for the travelling along the network. It measures
    # how many times is each node/edge used if we walk using the shortest paths from each node to every other.
    # We have two options how to measure betweenness on primal graph - on nodes or on edges.

    # Node-based
    # Node-based betweenness, as name suggests, measures betweennes of each node - how many times we would walk
    # through node.

    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_n', mode='nodes', weight='mm_len')

    momepy.mean_nodes(primal, 'betweenness_metric_n')

    # Edge-based
    # Edge-based betweenness does the same but for edges. How many times we go through each edge (street)
    primal = momepy.betweenness_centrality(primal, name='betweenness_metric_e', mode='edges', weight='mm_len')
    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    # Straightness
    # While both closeness and betweenness are generally used in many applications of network analysis, straightness
    # centrality is specific to street networks as it requires geographical element. It is measured as a ratio between real and
    # Euclidean distance while waking from each node to every other
    primal = momepy.straightness_centrality(primal)
    # nodes = momepy.nx_to_gdf(primal, lines=False)
    momepy.mean_nodes(primal, 'straightness')

    primal_gdf = momepy.nx_to_gdf(primal, points=False)

    ## closeness400
    gdf_proj_streets['closeness400']=primal_gdf.closeness400.values
    array_closeness400= primal_gdf.closeness400.values
    closeness400 = array_closeness400.tolist()

    ## closeness_global
    gdf_proj_streets['closeness_global']=primal_gdf.closeness_global.values
    array_closeness_global= primal_gdf.closeness_global.values
    closeness_global = array_closeness_global.tolist()

    ## betweenness_metric_n
    gdf_proj_streets['betweenness_metric_n']=primal_gdf.betweenness_metric_n.values
    array_betweenness_metric_n= primal_gdf.betweenness_metric_n.values
    betweenness_metric_n = array_betweenness_metric_n.tolist()

    ## betweenness_metric_e
    gdf_proj_streets['betweenness_metric_e']=primal_gdf.betweenness_metric_e.values
    array_betweenness_metric_e= primal_gdf.betweenness_metric_e.values
    betweenness_metric_e = array_betweenness_metric_e.tolist()

    ## straightness
    gdf_proj_streets['straightness']=primal_gdf.straightness.values
    array_straightness= primal_gdf.straightness.values
    straightness = array_straightness.tolist()

    #SPEED
    array_speed = gdf_proj_streets.speed_kph.values
    speed = array_speed.tolist()

    #TRAVEL
    array_travel = gdf_proj_streets.travel_time.values
    travel = array_travel.tolist()

    # # /////////////////////////////////////////////
    # G_proj = ox.projection.project_graph(G_projected, to_crs=crs)

    G_proj = ox.projection.project_graph(G_projected, to_crs=crs)
    #FOOD
    key_food_a = "amenity" 
    value_FOOD_a = ["bar",
                "biergarten",
                "restaurant",
                "food_court",
                "ice_cream",
                "pub",
                "cafe",
                "fast_food"]
    tags_food_a = {key_food_a: value_FOOD_a}

    key_food_b = "shop" 
    value_FOOD_b = ["alcohol",
                "bakery",
                "beverages",
                "brewing_supplies",
                "butcher",
                "cheese",
                "chocolate",
                "coffee",
                "confectionery",
                "convenience",
                "deli",
                "dairy",
                "frozen_food",
                "greengrocer",
                "health_food",
                "ice_cream",
                "pasta",
                "pastry",
                "seafood",
                "spices",
                "tea",
                "wine",
                "department_store",
                "general",
                "kiosk",
                "mall",
                "supermarket",
                "wholesale"]
    tags_food_b = {key_food_b: value_FOOD_b}

    tags_food = dict(tags_food_a, **tags_food_b)

    gdf_FOOD = ox.geometries.geometries_from_bbox(north, south, east, west, tags_food)
    gdf_pts_FOOD = gdf_FOOD.loc[gdf_FOOD.geometry.geometry.type=='Point']

    gdf_pts_proj_FOOD = ox.projection.project_gdf(gdf_pts_FOOD, to_crs=crs)
    # Calculate distances to
    G_dist_FOOD = ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_FOOD['geometry'].x, Y=gdf_pts_proj_FOOD['geometry'].y, interpolate=None, return_dist=False)
    # Count occurences in distance df
    occurences_FOOD = Counter(G_dist_FOOD)
    # Initialize empty list for values
    food = []
    # Map occurences to G_edge df
    for i in gdf_proj_streets.index:
        occurence_FOOD = occurences_FOOD[gdf_proj_streets.loc[i].name]
        food.append(occurence_FOOD)
    gdf_proj_streets['food'] = food
    # # /////////////////////////////////////////////

    # #education
    key_education = "amenity" 
    value_education = ["college",
                  "kindergarten",
                  "library",
                  "university",
                  "school"]

    tags_education = {key_education: value_education}
    gdf_education = ox.geometries.geometries_from_bbox(north, south, east, west, tags_education)
    gdf_pts_education = gdf_education.loc[gdf_education.geometry.geometry.type=='Point']

    gdf_pts_proj_education = ox.projection.project_gdf(gdf_pts_education, to_crs=crs)
    # Calculate distances to
    G_dist_education= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_education['geometry'].x, Y=gdf_pts_proj_education['geometry'].y, interpolate=None, return_dist=False)
    # Count occurences in distance df
    occurences_education = Counter(G_dist_education)
    # Initialize empty list for values
    education = []
    # Map occurences to G_edge df
    for i in gdf_proj_streets.index:
        occurence_education = occurences_education[gdf_proj_streets.loc[i].name]
        education.append(occurence_education)
    gdf_proj_streets['education'] = education
    # # /////////////////////////////////////////////

    # #transport
    key_transport = "amenity" 
    value_transport = ["bicycle_parking",
                  "bus_station",
                  "charging_station",
                  "ferry_terminal",
                  "fuel",
                  "motorcycle_parking",
                  "parking",
                  "parking_entrance",
                  "parking_space",
                  "taxi"]                

    tags_transport = {key_transport: value_transport}
    gdf_transport = ox.geometries.geometries_from_bbox(north, south, east, west, tags_transport)
    gdf_pts_transport = gdf_transport.loc[gdf_transport.geometry.geometry.type=='Point']

    gdf_pts_proj_transport = ox.projection.project_gdf(gdf_pts_transport, to_crs=crs)
    # Calculate distances to
    G_dist_transport= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_transport['geometry'].x, Y=gdf_pts_proj_transport['geometry'].y, interpolate=None, return_dist=False)
    # Count occurences in distance df
    occurences_transport = Counter(G_dist_transport)
    # Initialize empty list for values
    transport = []
    # Map occurences to G_edge df
    for i in gdf_proj_streets.index:
        occurence_transport = occurences_transport[gdf_proj_streets.loc[i].name]
        transport.append(occurence_transport)
    gdf_proj_streets['transport'] = transport
    # #shop
    key_shop = "shop" 
    value_shop = ["baby_goods",
                  "bag",
                  "boutique",
                  "clothes",
                  "fabric",
                  "fashion_accessories",
                  "jewelry",
                  "leather",
                  "sewing",
                  "shoes",
                  "tailor",
                  "watches",
                  "wool",
                  "charity",
                  "second_hand",
                  "variety_store",
                  "beauty",
                  "chemist",
                  "cosmetics",
                  "erotic",
                  "hairdresser",
                  "hairdresser_supply",
                  "hearing_aids",
                  "herbalist",
                  "perfumery",
                  "tattoo"]                

    tags_shop = {key_shop: value_shop}
    gdf_shop = ox.geometries.geometries_from_bbox(north, south, east, west, tags_shop)
    gdf_pts_shop = gdf_shop.loc[gdf_shop.geometry.geometry.type=='Point']

    gdf_pts_proj_shop = ox.projection.project_gdf(gdf_pts_shop, to_crs=crs)
    # Calculate distances to
    G_dist_shop= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_shop['geometry'].x, Y=gdf_pts_proj_shop['geometry'].y, interpolate=None, return_dist=False)
    # Count occurences in distance df
    occurences_shop = Counter(G_dist_shop)
    # Initialize empty list for values
    shop = []
    # Map occurences to G_edge df
    for i in gdf_proj_streets.index:
        occurence_shop = occurences_shop[gdf_proj_streets.loc[i].name]
        shop.append(occurence_shop)
    gdf_proj_streets['shop'] = shop
    # /////////////////////////////////////////////
    # #vegetation
    tags_vegetation = {
        'natural':True,
    }

    gdf_vegetation = ox.geometries.geometries_from_bbox(north, south, east, west, tags_vegetation)
    gdf_pts_vegetation = gdf_vegetation.loc[gdf_vegetation.geometry.geometry.type=='Point']

    gdf_pts_proj_vegetation = ox.projection.project_gdf(gdf_pts_vegetation, to_crs=crs)
    # Calculate distances to
    G_dist_vegetation= ox.distance.nearest_edges(G_proj, X= gdf_pts_proj_vegetation['geometry'].x, Y=gdf_pts_proj_vegetation['geometry'].y, interpolate=None, return_dist=False)
    # Count occurences in distance df
    occurences_vegetation = Counter(G_dist_vegetation)
    # Initialize empty list for values
    vegetation = []
    # Map occurences to G_edge df
    for i in gdf_proj_streets.index:
        occurence_vegetation = occurences_vegetation[gdf_proj_streets.loc[i].name]
        vegetation.append(occurence_vegetation)
    gdf_proj_streets['vegetation'] = vegetation

    # /////////////////////////////////////////////
    locations = [point]
    dt_string = '20211231'
    dt_stringfrom = '19901231'

    parameters = 'T2M,WS2M,WD2M,QV2M,CLOUD_AMT,TS,PW,DIRECT_ILLUMINANCE,DIFFUSE_ILLUMINANCE,ALLSKY_SFC_UVA'

    url = "https://power.larc.nasa.gov/api/temporal/daily/point?parameters="+parameters+"&community=RE&longitude={longitude}&latitude={latitude}&start="+dt_stringfrom+"&end="+dt_string+"&format=JSON"

    data = []
    base_url = url
    for latitude, longitude in locations:
        api_request_url = base_url.format(longitude=longitude, latitude=latitude)
        response = requests.get(url=api_request_url, verify=True, timeout=300.00) 
        content = json.loads(response.content.decode('utf-8'))
        dfa = pd.json_normalize(content['geometry'])
        dfb = pd.json_normalize(content['properties'])
        dfc = dfa.join(dfb)
        data.append(dfc)

    result = pd.concat(data)

    def get_climate_value(parameter_string, tag):
        """Get value of specific data"""
        new_points = pd.DataFrame()
        # new_points = address_nasa.iloc[[0]].copy()
        for i in range(2001,2022):
          a = 'df_new_year'+str(i)
          # print(a)
          b = result.copy()
          year = parameter_string + str(i)
          c = b.filter(like=year, axis=1)
          c_new = c.copy()
          anual = str(i)
          c_new[anual] = c_new.sum(axis=1)/len(c_new.columns)
          c_new = [float(u) for u in c_new[anual]]
          new_points[anual] = c_new
          new_points['tag'] = tag

        new_points_new = new_points.copy()
        new_points_new = new_points.melt(id_vars=["tag"], var_name="start_date")
        new_points_new = new_points_new[['start_date', 'tag','value']]
        new_points_new['value'] = new_points_new.rename({'value': 'value_'+tag}, axis=1, inplace=True)
        new_points_new = new_points_new[['start_date', 'tag','value_'+tag]]
        new_points_new['start_date'] = new_points_new['start_date'].astype(float)


        # Return indices and distances
        return (new_points_new)

    new_points_tm = get_climate_value('T2M.', 'temperature')
    new_points_ws = get_climate_value('WS2M.', 'windSpeed')

    new_points_wd = get_climate_value('WD2M.', 'windDirection')

    new_points_qv = get_climate_value('QV2M.', 'humidity')

    new_points_CLOUD_AMT = get_climate_value('CLOUD_AMT.', 'skyCover')

    new_points_TS = get_climate_value('TS.', 'earthTemperature')

    new_points_PW = get_climate_value('PW.', 'precipitationWater')

    new_points_DIRECT_ILLUMINANCE = get_climate_value('DIRECT_ILLUMINANCE.', 'directIlluminance')

    new_points_DIFFUSE_ILLUMINANCE = get_climate_value('DIFFUSE_ILLUMINANCE.', 'diffuseIlluminance')

    new_points_ALLSKY_SFC_UVA = get_climate_value('ALLSKY_SFC_UVA.', 'irradiation')
    
    def data(new_points,year):
        aaa = new_points.loc[new_points['start_date'] == year]
        value = aaa.iloc[:, 2].values[0]        
        return(value)
    year = 2021
    tempp = data(new_points_tm,year)  
    gdf_proj_streets['value_temperature'] =tempp  
    
    wss = data(new_points_ws,year)  
    gdf_proj_streets['value_windSpeed'] = wss

    wdd = data(new_points_wd,year)  
    gdf_proj_streets['value_windDirection'] = wdd

    qvv = data(new_points_qv,year)  
    gdf_proj_streets['value_humidity'] = qvv

    clsky = data(new_points_CLOUD_AMT,year)  
    gdf_proj_streets['value_skyCover'] = clsky

    TSs = data(new_points_TS,year)  
    gdf_proj_streets['value_earthTemperature'] = TSs

    PWw = data(new_points_PW,year)  
    gdf_proj_streets['value_precipitationWater'] = PWw

    DIRECT_ILLUMINANCEe = data(new_points_DIRECT_ILLUMINANCE,year)  
    gdf_proj_streets['value_directIlluminance'] = DIRECT_ILLUMINANCEe

    DIFFUSE_ILLUMINANCEe = data(new_points_DIFFUSE_ILLUMINANCE,year)  
    gdf_proj_streets['value_diffuseIlluminance'] = DIFFUSE_ILLUMINANCEe

    ALLSKY_SFC_UVAa = data(new_points_ALLSKY_SFC_UVA,year)  
    gdf_proj_streets['value_irradiation'] = ALLSKY_SFC_UVAa

    # address_nasa_year['x'] = address_nasa_year.geometry.x
    # address_nasa_year['y'] = address_nasa_year.geometry.y
    # address_nasa_year["start_date"] = year
    # address_nasa_year = address_nasa_year.loc[:,['start_date','tag','geometry','x','y','value_temperature','value_windSpeed','value_windDirection','value_humidity','value_skyCover','value_earthTemperature','value_precipitationWater','value_directIlluminance','value_diffuseIlluminance','value_irradiation','value_airQuality']]
    # address_nasa_year

    # address_nasa_year = pd.DataFrame()

    # address_nasa_year['start_date'] = new_points_tm['start_date']
    # address_nasa_year['value_temperature'] = new_points_tm['value_temperature']

    # address_nasa_year['value_windSpeed'] = new_points_ws['value_windSpeed']

    # address_nasa_year['value_windDirection'] = new_points_wd['value_windDirection']
    
    # address_nasa_year['value_humidity'] = new_points_qv['value_humidity']
    
    # address_nasa_year['value_skyCover'] = new_points_CLOUD_AMT['value_skyCover']

    # address_nasa_year['value_earthTemperature'] = new_points_TS['value_earthTemperature']

    # address_nasa_year['value_precipitationWater'] = new_points_PW['value_precipitationWater']

    # address_nasa_year['value_directIlluminance'] = new_points_DIRECT_ILLUMINANCE['value_directIlluminance']
    
    # address_nasa_year['value_diffuseIlluminance'] = new_points_DIFFUSE_ILLUMINANCE['value_diffuseIlluminance']

    # address_nasa_year['value_irradiation'] = new_points_ALLSKY_SFC_UVA['value_irradiation']

    # array_tm= address_nasa_year.value_temperature   
    # array_ws= address_nasa_year.value_windSpeed
    # array_wd= address_nasa_year.value_windDirection
    # array_qv= address_nasa_year.value_humidity
    # array_CLOUD_AMT= address_nasa_year.value_skyCover
    # array_TS= address_nasa_year.value_earthTemperature
    # array_PW= address_nasa_year.value_precipitationWater
    # array_DIRECT_ILLUMINANCE= address_nasa_year.value_directIlluminance
    # array_DIFFUSE_ILLUMINANCE= address_nasa_year.value_diffuseIlluminance
    # array_ALLSKY_SFC_UVA= address_nasa_year.value_irradiation

    # climate = array_tm.tolist() + array_ws.tolist() + array_wd.tolist() + array_qv.tolist() + array_CLOUD_AMT.tolist() + array_TS.tolist() + array_PW.tolist() + array_DIRECT_ILLUMINANCE.tolist() + array_DIFFUSE_ILLUMINANCE.tolist() + array_ALLSKY_SFC_UVA.tolist() 

    # /////////////////////////////////////////////
    # /////////////////////////////////////////////
    new_my_path = r'C:\ULT\static\images'
    new_my_file = 'DEM.tif'

    # dem_path = '/content/DEM.tif'
    # output =  dem_path

    # elevation.clip(bounds=bounds, output=output, product='SRTM1')

    dem_raster = rasterio.open(os.path.join(new_my_path, new_my_file))
    # src_crs = dem_raster.crs
    # src_shape = src_height, src_width = dem_raster.shape
    # src_transform = from_bounds(west, south, east, north, src_width, src_height)
    source = dem_raster.read(1)


    def hillshade(array, azimuth, angle_altitude):

      # Source: http://geoexamples.blogspot.com.br/2014/03/shaded-relief-images-using-gdal-python.html

      x, y = np.gradient(array)
      slope = np.pi/2. - np.arctan(np.sqrt(x*x + y*y))
      aspect = np.arctan2(-x, y)
      azimuthrad = azimuth*np.pi / 180.
      altituderad = angle_altitude*np.pi / 180.


      shaded = np.sin(altituderad) * np.sin(slope) \
      + np.cos(altituderad) * np.cos(slope) \
      * np.cos(azimuthrad - aspect)
      return 255*(shaded + 1)/2

    hillsource = hillshade(source, 30, 30)
    heights = hillsource.tolist()
    heightmap = [x for xs in heights for x in xs]

    inProj = Proj(init='epsg:4326')
    outProj = Proj(init='epsg:2062')
    west, south, east, north = bounds
    west2, south2 = transform(inProj,outProj,west, south)
    east2, north2= transform(inProj,outProj,east, north)

    extent = west2,  east2, south2, north2

    return gdf_proj_streets
    # return streets, buildings, widths, width_deviations, openness, closeness400, closeness_global, betweenness_metric_n, betweenness_metric_e, straightness, speed, travel, #food, education, transport, shop, vegetation, climate, heightmap, src_shape,
