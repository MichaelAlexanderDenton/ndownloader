available = ["tag", "artist", "character", "parody", "group"]

def create_search_query(base_url=None, **kwargs):
    query = ""
    for key, value in kwargs.items():
        value = value.lower().replace(" ", "+")
        query += "{0}={1}&".format(key, value)
    
    link = base_url + query
    print("Search URL: {0}".format(link))
    return link

            
            