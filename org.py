import requests

api_key = 'API_KEY_HERE' #***** ENTER Meraki API KEY HERE *****
base_url = 'https://api.meraki.com/api/v1'

headers = {
    'X-Cisco-Meraki-API-Key': api_key,
    'Content-Type': 'application/json'
}

def get_organizations():
    url = f"{base_url}/organizations"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    try:
        organizations = get_organizations()
        for org in organizations:
            print(f"Organization Name: {org['name']}, Organization ID: {org['id']}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
