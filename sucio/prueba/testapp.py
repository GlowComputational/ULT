from flask import Flask
import ghhops_server as hs

import test

app = Flask(__name__)
hops = hs.Hops(app)


@hops.component(
    "/grapghs",
    name = "graphs",
    # inputs=[
    #     hs.HopsString("Location", "Location", "Location", hs.HopsParamAccess.ITEM),
    #     hs.HopsInteger("Distance", "Distance", "Distance", hs.HopsParamAccess.ITEM),
    # ],

    outputs=[
        hs.HopsCurve("STREETS","STREETS","STREETS"),
        hs.HopsCurve("BUILDINGS","BUILDINGS","BUILDINGS"),
        # hs.HopsNumber("HEIGHTS","HEIGHTS","HEIGHTS"),
        # hs.HopsNumber("SHAPE_DEM","SHAPE_DEM","SHAPE_DEM"),
        # hs.HopsNumber("WIDTHS","WIDTHS","WIDTHS"),
        # hs.HopsNumber("WIDTHS_DEVIATIONS","WIDTHS_DEVIATIONS","WIDTHS_DEVIATIONS"),
        # hs.HopsNumber("OPENNESS","OPENNESS","OPENNESS"),
        # hs.HopsNumber("closeness400","closeness400","closeness400"),
        # hs.HopsNumber("closeness_global","closeness_global","closeness_global"),
        # hs.HopsNumber("betweenness_metric_n","betweenness_metric_n","betweenness_metric_n"),
        # hs.HopsNumber("betweenness_metric_e","betweenness_metric_e","betweenness_metric_e"),
        # hs.HopsNumber("straightness","straightness","straightness"),
        # hs.HopsNumber("SPEED","SPEED","SPEED"),
        # hs.HopsNumber("TRAVEL","TRAVEL","TRAVEL"),
        # hs.HopsNumber("Food","Food","Food"),
        # hs.HopsNumber("Education","Education","Education"),
        # hs.HopsNumber("Transport","Transport","Transport"),
        # hs.HopsNumber("Shop","Shop","Shop"),
        # hs.HopsNumber("Vegetation","Vegetation","Vegetation"),
        # hs.HopsNumber("CLIMATE","CLIMATE","CLIMATE"),
        
    ]
)

def thesisHops(place_point, distancia):
    return test.getEdges(place_point, distancia)


if __name__== "__main__":
    app.run(debug=True)