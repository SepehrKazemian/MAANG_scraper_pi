import requests

url = "https://boards-api.greenhouse.io/v1/boards/deepmind/jobs"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(response.json())
    for job in data.get("jobs", []):
        print(f"🔹 {job['title']} - {job['location']['name']}")
        print(f"🔗 {job['absolute_url']}\n")
else:
    print(f"❌ Failed to fetch jobs. Status code: {response.status_code}")