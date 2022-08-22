from flask import Flask, render_template, request
# import ghhops_server as hs

import test
import folium
import pandas as pd

app = Flask(__name__)
# hops = hs.Hops(app)

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template("home_index.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login_index.html')

@app.route("/result", methods=['GET', 'POST'])
def result():
    parameters = {
        'name',
        "travel_time",
        'speed_kph',
        'length',
        'widths',
        'width_deviations',
        'openness',
        'closeness400',
        'closeness_global',
        'betweenness_metric_n',
        'straightness',
        'food',
        'education',
        'transport',
        'shop',
        'vegetation',
        'value_temperature',
        'value_windSpeed',
        'value_windDirection',
        'value_humidity',
        'value_skyCover',
        'value_earthTemperature',
        'value_precipitationWater',
        'value_directIlluminance',
        'value_diffuseIlluminance',
        'value_irradiation',
    }

    location = request.form['location']
    distance = request.form['distance']
    proj_streets = test.getEdges(location, distance)

    folium_map = proj_streets.explore(
        column ='travel_time',
        tooltip_kwds=dict(labels=True),
        tooltip=parameters,
        popup=parameters,
        k=10,
        name="graph",
        tiles=None,
        )

    folium.TileLayer('cartodbpositron',opacity=0.6).add_to(folium_map)
    folium.LayerControl().add_to(folium_map)
    folium_map.save('templates/map.html')

    return render_template('map.html')

# @app.route("/result", methods=['GET', 'POST'])
# def result():
#     return render_template('index.html')



if __name__== "__main__":
    app.run(debug=True)