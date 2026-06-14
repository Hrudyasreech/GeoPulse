import requests 

api_key = "qLhX_Mbjl0PqQ8ox1Ir3MOtuwMhGBn-S9EQnFGSfRQvPHDnm"

url = (
    f"https://api.currentsapi.services/v1/search"
    f"?keywords=Tamil%20Nadu&language=en&page_size=15&apiKey={api_key}"
)

response = requests.get(url)
print(response.json())

