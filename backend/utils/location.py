import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """ 現在地と店舗の緯度経度から距離(km)を計算する (Haversineの公式) """
    R = 6371.0 # 地球の半径 (km)

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance # km単位

def estimate_walk_time(distance_km):
    """ 距離から徒歩の推定時間（分）を計算 (時速約4.8km想定) """
    # 1km = 12.5分 (時速4.8km)
    minutes = distance_km * 12.5
    return math.ceil(minutes) # 切り上げで返す
