import requests
import pymysql
import datetime
import sys
from pymysql.constants import CLIENT

db_user = 'DB_USERNAME_HERE'      #***** ENTER MariaDB or MySQL Username HERE (root by default)*****
db_password = 'DB_PASSWORD_HERE'  #***** ENTER MariaDB or MySQL Password HERE*****
db_host = '127.0.0.1'             #***** Stanard Host Port, shouldn't need to change unless you use a custom host *****
db_database = 'DB_NAME_HERE'      #***** ENTER MariaDB or MySQL DATABASE NAME HERE *****
api_key = 'API_KEY_HERE'          #***** ENTER Meraki API KEY HERE *****
organization_id = 'ORG_ID_HERE'   #***** ENTER ORGANIZATION ID HERE ******
base_url = 'https://api.meraki.com/api/v1'

headers = {
    'X-Cisco-Meraki-API-Key': api_key,
    'Content-Type': 'application/json'
}

def log_message(message):
    print(f"[{datetime.datetime.now()}] {message}")

def handle_exception(e, message=""):
    log_message(f"Error {message}: {e}")

def insert_test_data():
    test_data = {
        'SwitchPort': 'TestSwitch/1',
        'PortNumber': 1,
        'Name': 'TestPort',
        'Type': 'TestType',
        'VLAN': 99,
        'ReceivedBytes': 1000,
        'SentBytes': 2000,
        'Status': 'TestStatus',
        'Tags': 'TestTag',
        'PortProfile': 'TestProfile'
    }
    try:
        insert_data([test_data])
    except Exception as e:
        handle_exception(e, "inserting test data")

def update_summary_table():
    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO PortSummary (switch, port, day_of_week, hour_of_day, avg_received_bytes, avg_sent_bytes)
            SELECT switch, port, DAYOFWEEK(timestamp) as day_of_week, HOUR(timestamp) as hour_of_day,
                   AVG(received_bytes) as avg_received_bytes, AVG(sent_bytes) as avg_sent_bytes
            FROM SwitchPorts
            GROUP BY switch, port, DAYOFWEEK(timestamp), HOUR(timestamp)
            ON DUPLICATE KEY UPDATE avg_received_bytes=VALUES(avg_received_bytes), avg_sent_bytes=VALUES(avg_sent_bytes)
            """
            cursor.execute(sql)
            log_message("Summary table updated.")
        connection.commit()
    except Exception as e:
        handle_exception(e, "updating summary table")
    finally:
        connection.close()

def update_daily_summary():
    update_summary_table()

def get_networks(organization_id):
    try:
        url = f"{base_url}/organizations/{organization_id}/networks"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        networks = response.json()
        return networks
    except Exception as e:
        handle_exception(e, "fetching networks")
        return []

def fetch_device_serials(network_id):
    try:
        url = f"{base_url}/networks/{network_id}/devices"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        devices = response.json()
        switch_serials = [device['serial'] for device in devices if device.get('model', '').startswith('MS')]
        return switch_serials
    except Exception as e:
        handle_exception(e, "fetching device serials")
        return []

def fetch_port_statuses(serial):
    try:
        url = f"{base_url}/devices/{serial}/switch/ports"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        ports = response.json()
        return ports
    except Exception as e:
        handle_exception(e, "fetching port statuses")
        return []

def get_db_connection():
    try:
        connection = pymysql.connect(host=db_host, user=db_user, password=db_password, db=db_database, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, client_flag=CLIENT.MULTI_STATEMENTS)
        log_message("Database connection established")
        return connection
    except Exception as e:
        handle_exception(e, "establishing database connection")
        return None

def insert_data(port_data):
    connection = get_db_connection()
    if not connection:
        return

    try:
        with connection.cursor() as cursor:
            for port in port_data:
                cursor.execute(
                    """INSERT INTO SwitchPorts (switch, port, name, type, vlan, received_bytes, sent_bytes, status, tags, port_profile)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=%s, type=%s, vlan=%s, received_bytes=%s, sent_bytes=%s, status=%s, tags=%s, port_profile=%s""",
                    (port['SwitchPort'], port['PortNumber'], port['Name'], port['Type'], port['VLAN'], port['ReceivedBytes'],
                     port['SentBytes'], port['Status'], port['Tags'], 
                     port['PortProfile'], port['Name'], port['Type'], port['VLAN'], port['ReceivedBytes'],
                     port['SentBytes'], port['Status'], port['Tags'], port['PortProfile'])
                )
        connection.commit()
    except Exception as e:
        handle_exception(e, "inserting data")
    finally:
        connection.close()

def compare_data(existing_data, new_data):
    changes = {}
    for key in ['name', 'type', 'vlan', 'received_bytes', 'sent_bytes', 'status', 'tags', 'port_profile']:
        if existing_data.get(key) != new_data.get(key):
            changes[key] = {
                'old': existing_data.get(key),
                'new': new_data.get(key)
            }
    return changes

def log_changes(changes, switch_port, port_number):
    connection = get_db_connection()
    if connection is None:
        return

    try:
        with connection.cursor() as cursor:
            for key, value in changes.items():
                cursor.execute(
                    """INSERT INTO PortChanges (switch, port, attribute, old_value, new_value)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (switch_port, port_number, key, value['old'], value['new'])
                )
        connection.commit()
    except Exception as e:
        handle_exception(e, "logging changes")
    finally:
        connection.close()

def check_and_log_deviations():
    connection = get_db_connection()
    if not connection:
        return

    deviations_found = False

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT switch, port, received_bytes, sent_bytes FROM SwitchPorts")
        current_usage = cursor.fetchall()

        for usage in current_usage:
            switch = usage['switch']
            port = usage['port']
            received_bytes = usage['received_bytes']
            sent_bytes = usage['sent_bytes']

            day_of_week = datetime.datetime.today().weekday() + 1
            hour_of_day = datetime.datetime.now().hour

            cursor.execute("""SELECT avg_received_bytes, avg_sent_bytes FROM PortSummary
                              WHERE switch = %s AND port = %s AND day_of_week = %s AND hour_of_day = %s""",
                           (switch, port, day_of_week, hour_of_day))
            average_usage = cursor.fetchone()

            if average_usage:
                avg_received_bytes = average_usage['avg_received_bytes']
                avg_sent_bytes = average_usage['avg_sent_bytes']
                deviation_message = []

                if received_bytes > avg_received_bytes * 1.5:
                    deviation_message.append(f"High received bytes: {received_bytes} (avg: {avg_received_bytes})")
                elif received_bytes < avg_received_bytes * 0.5:
                    deviation_message.append(f"Low received bytes: {received_bytes} (avg: {avg_received_bytes})")

                if sent_bytes > avg_sent_bytes * 1.5:
                    deviation_message.append(f"High sent bytes: {sent_bytes} (avg: {avg_sent_bytes})")
                elif sent_bytes < avg_sent_bytes * 0.5:
                    deviation_message.append(f"Low sent bytes: {sent_bytes} (avg: {avg_sent_bytes})")

                if deviation_message:
                    message = ", ".join(deviation_message)
                    deviations_found = True
                else:
                    message = "No deviations"

                cursor.execute("""INSERT INTO DeviationLogs (switch, port, timestamp, message)
                                  VALUES (%s, %s, %s, %s)""",
                               (switch, port, datetime.datetime.now(), message))

        if not deviations_found:
            cursor.execute("""INSERT INTO DeviationLogs (timestamp, message)
                              VALUES (%s, %s)""",
                           (datetime.datetime.now(), "No deviations on check"))

        connection.commit()

    except Exception as e:
        print(f"Error checking and logging deviations: {e}")
    finally:
        cursor.close()
        connection.close()

def main():
    connection = get_db_connection()
    if connection is None:
        return
    
    try:
        networks = get_networks(organization_id)
        if not networks:
            print("No networks data received from API")
            return

        for network in networks:
            network_id = network['id']
            switch_serials = fetch_device_serials(network_id)
            
            for serial in switch_serials:
                port_statuses = fetch_port_statuses(serial)

                for port_status in port_statuses:
                    with connection.cursor() as cursor:
                
                        switch = serial
                        port_number = port_status['portId']
                        name = port_status.get('name', 'Unknown')
                        port_type = port_status.get('type', 'N/A')
                        vlan = port_status.get('vlan', 0)
                        received_bytes = port_status.get('usage', {}).get('received', 0)
                        sent_bytes = port_status.get('usage', {}).get('sent', 0)
                        status = 'Connected' if port_status.get('enabled', False) else 'Disconnected'
                        tags = ';'.join(port_status.get('tags', []))
                        port_profile = port_status.get('portProfile', 'N/A')

                        cursor.execute("SELECT * FROM SwitchPorts WHERE switch = %s AND port = %s", (switch, port_number))
                        existing_data = cursor.fetchone()

                        if existing_data:
                            changes = compare_data(existing_data, {
                                'name': name,
                                'type': port_type,
                                'vlan': vlan,
                                'received_bytes': received_bytes,
                                'sent_bytes': sent_bytes,
                                'status': status,
                                'tags': tags,
                                'port_profile': port_profile
                            })
                            if changes:
                                log_changes(changes, switch, port_number)
                    
                        cursor.execute(
                            """INSERT INTO SwitchPorts (switch, port, name, type, vlan, received_bytes, sent_bytes, status, tags, port_profile)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE name=%s, type=%s, vlan=%s, received_bytes=%s, sent_bytes=%s, status=%s, tags=%s, port_profile=%s""",
                            (switch, port_number, name, port_type, vlan, received_bytes, sent_bytes, status, tags, port_profile,
                             name, port_type, vlan, received_bytes, sent_bytes, status, tags, port_profile)
                        )
                    connection.commit()
        check_and_log_deviations()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'update_summary':
        update_daily_summary()
    else:
        main()
