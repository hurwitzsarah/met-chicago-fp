import json
import requests
import matplotlib.pyplot as plt
import os
import sqlite3
import unittest
import numpy as np
import re

def setUpDatabase(db_name):
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path+'/'+db_name)
    cur = conn.cursor()
    return cur, conn

def met_get_ids(cur, conn, query):
    search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
    p = {"q" : query}
    res = requests.get(search_url, params = p)
    data = json.loads(res.text)
    object_ids = data['objectIDs']
    cur.execute("CREATE TABLE IF NOT EXISTS object_ids (id INTEGER PRIMARY KEY, met_id INTEGER)")
    for i in range(len(object_ids)):
        cur.execute("INSERT OR IGNORE INTO object_ids (id,met_id) VALUES (?,?)",(i,object_ids[i]))
    conn.commit()
    return object_ids

def met_add_to_database(cur, conn, query, start, end):
    cur.execute("CREATE TABLE IF NOT EXISTS met_objects (object_id INTEGER PRIMARY KEY, is_highlight TEXT, title TEXT, artist_name TEXT, object_enddate INTEGER, objectname TEXT, medium TEXT)")
    conn.commit()
    no_repeats_names = []
    no_repeats_mediums = []
    no_repeats_artists = []
    object_ids = met_get_ids(cur, conn, query)
    for id in object_ids[start:end]:
        try:
            object_url = "https://collectionapi.metmuseum.org/public/collection/v1/objects/" + str(id)
            res = requests.get(object_url)
            data = json.loads(res.text)
        except:
            return "Exception"
        for k, v in data.items():
            if v!= None:
                object_id = int(data.get("objectID", 0))
                cur.execute("SELECT id FROM object_ids WHERE met_id = ?", (object_id,))
                id = int(cur.fetchone()[0])
                is_highlight = data.get("isHighlight", 0)
                title = data.get("title", 0)
                object_enddate = data.get("objectEndDate", 0)
                artist_name = data.get("artistDisplayName", 0)
                objectname = data.get("objectName", 0)
                medium = data.get("medium", 0)
                cur.execute('''INSERT or ignore INTO met_objects (object_id, artist_name, title, object_enddate, objectname, medium, is_highlight) 
                VALUES (?,?,?,?,?,?,?)''',(id, title, artist_name, object_enddate, objectname, medium, is_highlight))
            conn.commit()
        
def met_create_name_table(cur, conn):
    cur.execute('''SELECT met_objects.objectname FROM met_objects''')
    conn.commit()
    names = cur.fetchall()
    no_repeats_names = []
    for tup in names:
        name = tup[0]
        if name not in no_repeats_names:
            no_repeats_names.append(name)

    cur.execute("CREATE TABLE IF NOT EXISTS met_names (name_id INTEGER PRIMARY KEY, objectname TEXT)")
    for i in range(len(no_repeats_names)):
        cur.execute('''INSERT or ignore INTO met_names (name_id, objectname) VALUES (?,?)''',(i, no_repeats_names[i]))

def met_create_medium_table(cur, conn):
    cur.execute('''SELECT met_objects.medium FROM met_objects''')
    conn.commit()
    mediums = cur.fetchall()
    no_repeats_mediums = []
    for tup in mediums:
        medium = tup[0]
        if medium not in no_repeats_mediums:
            no_repeats_mediums.append(medium)

    cur.execute("CREATE TABLE IF NOT EXISTS met_mediums (medium_id INTEGER PRIMARY KEY, medium TEXT)")
    for i in range(len(no_repeats_mediums)):
        cur.execute('''INSERT or ignore INTO met_mediums (medium_id, medium) VALUES (?,?)''',(i, no_repeats_mediums[i]))

def met_create_artist_table(cur, conn):
    cur.execute('''SELECT met_objects.artist_name FROM met_objects''')
    conn.commit()
    artists = cur.fetchall()
    no_repeats_artists = []
    for tup in artists:
        artist = tup[0]
        if artist not in no_repeats_artists:
            no_repeats_artists.append(artist)

    cur.execute("CREATE TABLE IF NOT EXISTS met_artists (artist_id INTEGER PRIMARY KEY, artist_name TEXT)")
    for i in range(len(no_repeats_artists)):
        cur.execute('''INSERT or ignore INTO met_artists (artist_id, artist_name) VALUES (?,?)''',(i, no_repeats_artists[i]))

def met_dates_and_highlights(cur, conn, file): 
    cur.execute('''SELECT met_objects.object_enddate, met_objects.is_highlight FROM met_objects JOIN object_ids 
    ON met_objects.object_id = object_ids.id WHERE met_objects.is_highlight = ?''', (1,))
    conn.commit()
    lst = cur.fetchall()
    highlight_counts = {}
    count = 0
    total = 0
    for tup in lst:
        year = tup[0]
        total += year
        count += 1
        highlight_counts[year] = highlight_counts.get(year, 0) + 1
    avg = int(total/count)

    f = open(file, "w")
    f.write("The average year with the most highlighted 'activism' pieces was " + str(avg) + "\n")
    f.write("The total number of highlighted 'activism' items in this sample of 100 'activism' items was " + str(count) + "\n")
    f.close()

    years = list(highlight_counts.keys())
    counts = list(highlight_counts.values())
    x1 = np.array(years)
    y1 = np.array(counts)
    plt.scatter(x1, y1)
    plt.xlabel("Year")
    plt.ylabel("Number of Highlighted Pieces")
    plt.title("Highlighted Pieces By Year at the Met")
    plt.show()

def met_names_and_highlights(cur, conn, file):
    #average year of when most activist pieces were created in a sample of 100 items at the met
    #count of highlights and which years had the most highlighted pieces 
    #make one more based on my data for EC
    cur.execute('''SELECT met_names.name_id, met_objects.is_highlight FROM met_objects JOIN met_names 
    ON met_objects.objectname = met_names.name_id WHERE met_objects.is_highlight = ?''', (1,))
    conn.commit()
    lst = cur.fetchall()
    object_counts = {}
    for tup in lst:
        name = tup[0]
        object_counts[name] = object_counts.get(name, 0) + 1
    sorteddic = sorted(object_counts, key = lambda k: object_counts[k], reverse = True)
    most = sorteddic[0]
    f = open(file, "a")
    f.write("The object type id with the most highlighted 'activism' pieces was " + str(most) + ", with " + str(object_counts[most]) + " higlighted pieces.\n")
    f.close()

    names = list(object_counts.keys())
    names_counts = list(object_counts.values())

    x2 = np.array(names)
    y2 = np.array(names_counts)
    plt.bar(x2, y2, color='pink')
    plt.xlabel("Object Type Ids")
    plt.xticks(list(range(0, 49, 2)))
    plt.ylabel("Number of Highlighted Pieces")
    plt.title("Highlighted Pieces By Object Type Id at the Met")
    plt.show()

def met_extra_credit_viz(cur, conn, file):
    cur.execute('''SELECT met_objects.objectname, met_mediums.medium FROM met_objects JOIN met_mediums 
    ON met_objects.medium = met_mediums.medium_id WHERE met_objects.objectname = ?''', (3,))
    conn.commit()
    lst = cur.fetchall()
    medium_counts = {}
    for tup in lst:
        medium = tup[1]
        medium_counts[medium] = medium_counts.get(medium, 0) + 1
    sorteddic = sorted(medium_counts, key = lambda k: medium_counts[k], reverse = True)
    most = sorteddic[0]
    f = open(file, "a")
    f.write("Of the object type with the most highlighted 'activism' pieces, the most used medium was " + most + ".\n")
    f.close()

    y = np.array(list(medium_counts.values()))
    mediums = list(medium_counts.keys())
    mycolors = ["Plum", "PaleVioletRed", "PowderBlue", "OliveDrab", "LightCoral", "DarkSeaGreen", "DarkCyan", "CornflowerBlue", "Thistle", "RosyBrown", "PeachPuff", "LightSlateGrey", "LemonChiffon", "Lavender", "LightPink"]
    plt.pie(y, labels = mediums, colors = mycolors) 
    plt.title("'Activist' Paintings By Medium at the Met")
    plt.show()

def met_update_table(cur, conn):
    cur.execute('''SELECT artist_id, artist_name FROM met_artists''')
    conn.commit()
    artist_ids = cur.fetchall()
    no_repeats_ids = []
    for tup in artist_ids:
        id = tup[0]
        artist_name = tup[1]
        if id not in no_repeats_ids:
            no_repeats_ids.append(id)
        cur.execute("UPDATE met_objects SET artist_name = ? WHERE artist_name = ?", (id, artist_name))
    conn.commit()

    cur.execute('''SELECT medium_id, medium FROM met_mediums''')
    conn.commit()
    medium_ids = cur.fetchall()
    no_repeats_ids = []
    for tup in medium_ids:
        id = tup[0]
        medium = tup[1]
        if id not in no_repeats_ids:
            no_repeats_ids.append(id)
        cur.execute("UPDATE met_objects SET medium = ? WHERE medium = ?", (id, medium))
    conn.commit()

    cur.execute('''SELECT name_id, objectname FROM met_names''')
    conn.commit()
    name_ids = cur.fetchall()
    no_repeats_ids = []
    for tup in name_ids:
        id = tup[0]
        objectname = tup[1]
        if id not in no_repeats_ids:
            no_repeats_ids.append(id)
        cur.execute("UPDATE met_objects SET objectname = ? WHERE objectname = ?", (id, objectname))
    conn.commit()

def chi_get_ids(cur, conn, query, limit = 100):
    search_url = "https://api.artic.edu/api/v1/artworks/search?"
    p = {"q" : query, "limit" : limit}
    res = requests.get(search_url, params = p)
    data = json.loads(res.text)

    object_ids = []
    for item in data['data']:
        object_ids.append(item['id'])
    cur.execute("CREATE TABLE IF NOT EXISTS chi_object_ids (id INTEGER PRIMARY KEY, chicago_id INTEGER)")
    for i in range(len(object_ids)):
        cur.execute("INSERT OR IGNORE INTO chi_object_ids (id,chicago_id) VALUES (?,?)",(i,object_ids[i]))
    conn.commit()
    return object_ids

def chi_add_to_database(cur, conn, query, db_filename, start, end):
    cur.execute("CREATE TABLE IF NOT EXISTS chicago_objects (object_id INTEGER PRIMARY KEY, title TEXT, artist_name TEXT, object_enddate INTEGER, medium TEXT, origin TEXT, popularity TEXT)")
    conn.commit()
    
    object_ids = chi_get_ids(cur, conn, query)
    for id in object_ids[start:end]:
        try:
            object_url = "https://api.artic.edu/api/v1/artworks?ids=" + str(id) 
            res = requests.get(object_url)
            data = json.loads(res.text)
            art_data = data.get("data", 0)
        
            for item in art_data:
                if "id" in item:
                    object_id = int(item.get("id", 0))
                    title = item.get("title", 0)
                    name = item.get("artist_title", 0)
                    date_complete = int(item.get("date_end", 0))
                    art_type = item.get("artwork_type_title", 0)
                    origin = item.get("place_of_origin", 0)
                    popularity = item.get("has_not_been_viewed_much", 0)
                    # print((title, name, date_complete, art_type, origin, popularity))
                    cur.execute('''INSERT or ignore INTO chicago_objects (object_id, title, artist_name, object_enddate, medium, origin, popularity) 
                                VALUES (?,?,?,?,?,?,?)''',(object_id, title, name, date_complete, art_type, origin, popularity))
                conn.commit()

        except:
            print("error in add to database")

def chi_no_repeats(cur, conn, query):

    object_ids = chi_get_ids(cur, conn, query)
    for id in object_ids:
        try:
            object_url = "https://api.artic.edu/api/v1/artworks?ids=" + str(id) 
            res = requests.get(object_url)
            data = json.loads(res.text)
            art_data = data.get("data", 0)

            for item in art_data:
                if "id" in item:
                    name = item.get("artist_title", 0)
                    art_type = item.get("artwork_type_title", 0)
                    origin = item.get("place_of_origin", 0)
                    # print((name, art_type, origin))

            cur.execute("SELECT name_id FROM chicago_names WHERE artist_name = ?", (name,)) # name
            name_id = int(cur.fetchone()[0])
            cur.execute("UPDATE chicago_objects SET artist_name = ? WHERE artist_name = ?", (name_id, name))

            cur.execute("SELECT medium_id FROM chicago_mediums WHERE medium_type = ?", (art_type,)) # medium
            medium_id = int(cur.fetchone()[0])
            cur.execute("UPDATE chicago_objects SET medium = ? WHERE medium = ?", (medium_id, art_type))

            cur.execute("SELECT origin_id FROM chicago_origins WHERE origin_type = ?", (origin,)) # origin
            origin_id = int(cur.fetchone()[0])
            cur.execute("UPDATE chicago_objects SET origin = ? WHERE origin = ?", (origin_id, origin))

        except:
            pass              

    conn.commit()

def chi_create_name_table(cur, conn):
    cur.execute('''SELECT chicago_objects.artist_name FROM chicago_objects''')
    conn.commit()
    names = cur.fetchall()
    no_repeats_names = []
    for tup in names:
        name = tup[0]
        if name not in no_repeats_names:
            no_repeats_names.append(name)

    cur.execute("CREATE TABLE IF NOT EXISTS chicago_names (name_id INTEGER PRIMARY KEY, artist_name TEXT)")
    for i in range(len(no_repeats_names)):
        cur.execute('''INSERT or ignore INTO chicago_names (name_id, artist_name) VALUES (?,?)''',(i, no_repeats_names[i]))
    conn.commit()

def chi_create_medium_table(cur, conn):
    cur.execute('''SELECT chicago_objects.medium FROM chicago_objects''')
    conn.commit()
    mediums = cur.fetchall()
    no_repeats_mediums = []
    for tup in mediums:
        medium = tup[0]
        if medium not in no_repeats_mediums:
            no_repeats_mediums.append(medium)

    cur.execute("CREATE TABLE IF NOT EXISTS chicago_mediums (medium_id INTEGER PRIMARY KEY, medium_type TEXT)")
    for i in range(len(no_repeats_mediums)):
        cur.execute('''INSERT or ignore INTO chicago_mediums (medium_id, medium_type) VALUES (?,?)''',(i, no_repeats_mediums[i]))
    conn.commit()

def chi_create_origin_table(cur, conn):
    cur.execute('''SELECT chicago_objects.origin FROM chicago_objects''')
    conn.commit()
    origins = cur.fetchall()
    no_repeats_origins = []
    for tup in origins:
        origin = tup[0]
        if origin not in no_repeats_origins:
            no_repeats_origins.append(origin)

    cur.execute("CREATE TABLE IF NOT EXISTS chicago_origins (origin_id INTEGER PRIMARY KEY, origin_type TEXT)")
    for i in range(len(no_repeats_origins)):
        cur.execute('''INSERT or ignore INTO chicago_origins (origin_id, origin_type) VALUES (?,?)''',(i, no_repeats_origins[i]))
    conn.commit()

def chi_century_years(cur, conn): 
    cur.execute('''SELECT chicago_objects.object_enddate FROM chicago_objects''')
    conn.commit()
    years = cur.fetchall()
    century_dict = {} # key is century and value is list of years
    for year in years: 
        year = str(year[0])
        for i in range(12,21):
            regex = f"{str(i)}\d\d"
            if re.search(regex, year) != None:
                century = str(i) + "00"
                if century not in century_dict:
                    century_dict[century] = []
                century_dict[century].append(year)
    return century_dict

def chi_century_counts(cur, conn):
    century_dict = chi_century_years(cur, conn)
    century_count = {}
    for century in century_dict:
        count = len(century_dict[century])
        century_count[century] = count
    return dict(sorted(century_count.items())) # key is century value is count of years 

def chi_plot_century_count(cur, conn):
    century_dict = chi_century_counts(cur, conn)
    centuries = list(century_dict.keys())
    #y_pos = np.arange(centuries)
    counts = list(century_dict.values())
    plt.barh(centuries, counts, color = 'plum')
    plt.xlabel("Years Count")
    plt.ylabel("Century")
    plt.title("Amount of Activism Artworks Created in Each Century")
    plt.show()

def chi_origin_counts(cur, conn): 
    cur.execute('''SELECT chicago_objects.origin FROM chicago_objects''')
    cur.execute('''SELECT chicago_origins.origin_type FROM chicago_origins JOIN chicago_objects
    ON chicago_objects.origin = chicago_origins.origin_id''')
    conn.commit()
    origins = cur.fetchall()
    origin_dict = {}
    for origin in origins:
        origin = origin[0]
        if origin not in origin_dict:
            origin_dict[origin] = 0
        origin_dict[origin] += 1
    return origin_dict 

def chi_plot_origin_count(cur, conn):
    origin_dict = chi_origin_counts(cur, conn)
    dict5 = {}
    for k, v in origin_dict.items():
        if int(v) > 4:
            dict5[k] = v
            # 5 or more!

    labels = list(dict5.keys())
    counts = list(dict5.values())
    colors = ['yellowgreen', 'gold', 'lightskyblue', 'lightcoral', 'orange', 'plum']
    patches, texts = plt.pie(counts, labels=labels, colors=colors)
    plt.legend(patches, labels, loc = "best")
    plt.axis("equal")
    plt.title("Most Popular Origins of Chicago Activism Artworks")
    plt.tight_layout()
    plt.show()

def chi_write_file(cur, conn):
    years = chi_century_years(cur, conn)
    centuries = chi_century_counts(cur, conn)
    countries = chi_origin_counts(cur, conn)

    with open('calculations.txt', 'a') as convert_file:
        convert_file.write("\n")
        convert_file.write("\n")
        convert_file.write("List of years that activism artwork was made in each century (chicago)")
        convert_file.write("\n")
        convert_file.write(json.dumps(years)) # keys are centuries, values are lists of years

        convert_file.write("\n")
        convert_file.write("\n")
        convert_file.write("The count of years activism artwork was made in each century (chicago)")
        convert_file.write("\n")
        convert_file.write(json.dumps(centuries)) # keys are centuries, values are counts

        convert_file.write("\n")
        convert_file.write("\n")
        convert_file.write("The count of activism artworks that were created in each country (chicago)")
        convert_file.write("\n")
        convert_file.write(json.dumps(countries)) # keys are countries, valaues are counts 

def main():
    cur, conn = setUpDatabase("chicago_met_data.db")
    met_add_to_database(cur, conn, "activism", 0, 25)
    met_add_to_database(cur, conn, "activism", 25, 50)
    met_add_to_database(cur, conn, "activism", 50, 75)
    met_add_to_database(cur, conn, "activism", 75, 100)
    met_create_name_table(cur, conn)
    met_create_medium_table(cur, conn)
    met_create_artist_table(cur, conn)
    met_update_table(cur, conn)
    met_dates_and_highlights(cur, conn, 'calculations.txt')
    met_names_and_highlights(cur, conn, 'calculations.txt')
    met_extra_credit_viz(cur, conn, 'calculations.txt')

    chi_add_to_database(cur, conn, "activism","chicago_met_data.db", 0, 25)
    chi_add_to_database(cur, conn, "activism","chicago_met_data.db", 25, 50)
    chi_add_to_database(cur, conn, "activism","chicago_met_data.db", 50, 75)
    chi_add_to_database(cur, conn, "activism","chicago_met_data.db", 75, 100) # one has exception
    chi_create_name_table(cur, conn)
    chi_create_medium_table(cur, conn)
    chi_create_origin_table(cur, conn)
    chi_no_repeats(cur, conn, "activism")
    chi_plot_century_count(cur, conn)
    chi_plot_origin_count(cur, conn)
    chi_write_file(cur, conn)

if __name__ == "__main__":
    main()