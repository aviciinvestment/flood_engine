import geemap

def create_map():
    m = geemap.Map(
        basemap="CyclOSM",
        zoom=3
    )
    return m


def add_layer(m, image, vis, name):
    m.addLayer(image, vis, name)
    return m