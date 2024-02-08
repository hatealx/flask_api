from flask import Flask, send_file
from flask_restful import Resource , Api
import cv2
import numpy as np
import tempfile
import time


def map_creator(data):
    img = cv2.imread('map_image.jpg')         
    data = data.replace("\"", "")
    data = data.replace("\'", "")
    def compute_XY_from_GR(gr_east, gr_north):      # Compute XY pixel position within the jpg from Grid Reference

        # Grid Reference and Pixel coordinates of a point near the centre of the map
        data = (50481, 98019, 644, 534)  # Grid reference (Eastings, Northings) then pixel posn (x, y)

        base_es = data[0]
        base_ns = data[1]
        base_x = data[2]            # 644
        base_y = data[3]            # 534

        x = round(base_x + ((gr_east - base_es) * 0.3555))
        y = round(base_y - ((gr_north - base_ns) * 0.355))

        x_corr = round((y - base_y) * 0.04)     # apply a correction factor to the X coord. based on Y
        x -= x_corr

        y_corr = round((x - base_x) * 0.025)    # apply a correction factor to the Y coord, based on X
        y += y_corr
        return x, y


    def write_text_info(image, tax, ver, count):
        # Write the species name etc. and the key on the right iof the screen explaining the colours and ages
        cv2.putText(image, tax, (675, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(image, ver, (675, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        ctrstr = f"{count} sightings"
        cv2.putText(image, ctrstr, (675, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        cv2.putText(image, "< 2 years", (1400, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        cv2.putText(image, "< 5 years", (1400, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 255), 2)
        cv2.putText(image, "< 10 years", (1400, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.putText(image, "< 20 years", (1400, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
        cv2.putText(image, "20 years+", (1400, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)


    def draw_cross(image, point, pc, age):
        # pc is the percentage of sightings at this particular grid ref

        if pc > 20:
            sizer, thickness = 12, 3
        elif pc > 10:
            sizer, thickness = 9, 2
        else:
            sizer, thickness = 6, 1

        # use colour to represent age of most recent sighting at this grid ref
        #           0=blue        1=mauve       2=red         3=orange         4=yellow
        colors = [(255, 0, 0), (255, 0, 255), (0, 0, 255), (0, 128, 255), (0, 255, 255)]
        idx = 0
        if age < 2:
            idx = 4
        elif age < 5:
            idx = 3
        elif age < 10:
            idx = 2
        elif age < 20:
            idx = 1

        color = colors[idx]

        cv2.line(image, (point[0] - sizer, point[1]), (point[0] + sizer, point[1]), color, thickness)
        cv2.line(image, (point[0], point[1] - sizer), (point[0], point[1] + sizer), color, thickness)


    now = int(time.time())          # use time.time() to work out the current year
    days = now // 86400             # Days since 1/1/1970
    year_now = 1970 + int(days / 365.25)


    # fline Sample: amphibian/Triturus cristatus/Great Crested Newt/9/TV514989-1-2001/TV513989-7-1998/TV514990-1-2016/
    # Line holds species group name/species taxon name/common name/count/ then (grid ref - count - year) multiple times
    fsplit = data.split("*")      # Group/Taxon/Common/Total/GR-List
    group = fsplit.pop(0).strip()

    taxon = fsplit.pop(0).strip()
    taxon = taxon.capitalize()
    vernac = fsplit.pop(0).strip()              # Vernacular (Common) name
    vernac = vernac.title()
    total = int(fsplit.pop(0))                  # Total number of sightings of this species

    sp_refs = []

    griddata = fsplit.copy()                    # e.g. TV514989-1-2001/TV513989-7-1998/TV514990-1-2016/

    for triple in griddata:
        if not triple:
            break
        psplit = triple.split('~')
        print(psplit)               # GridRef - qty - latest year
        gr = psplit[0]                              # get grid ref
        gr = gr[:5] + "50" + gr[5:] + "50" 
                 # Adjust grid rwf to centre of 100m square
        ctr = psplit[1]
        year = psplit[2]
        sp_refs.append([gr, ctr, year])

    more = vernac
    if vernac.lower() == taxon.lower():             # if common name is same as taxon, use group name as common
        more = group
    more = more.title()

    write_text_info(img, taxon, more, total)         # Draw the text about ages on right side of the map image

    for item in sp_refs:
        if not item:
            break
        gr = item[0]                    # Grid Ref
        ctr = item[1]                   # Qty seen at this Grid Ref
        year = item[2]                  # Year of most recent sighting at this Grid Ref
        eastings = int(gr[2:7])         # split numeric part of Grid Ref into Eastings and Northings
        northings = int(gr[7:])

        ctr = int(ctr)                                  # Qty seen at this location
        pc = (ctr * 100) // total                       # Percent qty seen at this location compared to all locations

        x, y = compute_XY_from_GR(eastings, northings)      # Convert Grid Ref to pixel positions X, Y

        aged = year_now - int(year)                     # Age of most recent sighting at this Grid Ref

        draw_cross(img, (x, y), pc, aged )              # Draw a cross on the map at centre of this grid ref.
        # print(f"{eastings=} {northings=} {x=} {y=}")
    return img



app = Flask("map_api")
api = Api(app)

class Map(Resource):
    def get(self, data):
        try:
            final_map = map_creator(data)
        except:
            return "bad data"
        # Save the numpy array to a temporary file
        _, temp_filename = tempfile.mkstemp(suffix=".png")
        cv2.imwrite(temp_filename, final_map)

        return send_file(temp_filename, mimetype='image/png')
    

api.add_resource(Map, '/get_map/<data>')

if __name__ == "__main__":
    app.run(debug=True)
