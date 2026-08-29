import requests

response = requests.get("http://localhost:8080/account")
data = response.json()

print("Account status via Go service:", data["status"])
print("Buying power via Go service:", data["buying_power"])
