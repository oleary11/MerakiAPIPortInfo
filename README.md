**Meraki API Port Information**

This is a tool designed to give more accurate and consistent info about the ports in a Meraki Organization.

**Neccesary Actions**

To use this tool 2 main things need to be done:

 1. Set up a MariaDB or MySQL database (table structure shown below):
    - Table instructions here:
      - Switch Ports Table
      ```SQL
      CREATE TABLE SwitchPorts (
       switch VARCHAR(255) NOT NULL,
       port INT NOT NULL,
       name VARCHAR(255),
       type VARCHAR(50),
       vlan INT,
       received_bytes BIGINT,
       sent_bytes BIGINT,
       status VARCHAR(50),
       tags VARCHAR(255),
       port_profile VARCHAR(255),
       PRIMARY KEY (switch, port)
      );
      ```
      - Port Summary Table
      ```SQL
      CREATE TABLE PortSummary (
        switch VARCHAR(255) NOT NULL,
        port INT NOT NULL,
        day_of_week INT NOT NULL,
        hour_of_day INT NOT NULL,
        avg_received_bytes BIGINT,
        avg_sent_bytes BIGINT,
        PRIMARY KEY (switch, port, day_of_week, hour_of_day)
      );
      ```
      - Port Changes Table
      ```SQL
      CREATE TABLE PortChanges (
        switch VARCHAR(255) NOT NULL,
        port INT NOT NULL,
        attribute VARCHAR(50) NOT NULL,
        old_value VARCHAR(255),
        new_value VARCHAR(255),
        TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (switch, port, attribute, TIMESTAMP)
      );
      ```
      - Deviation Logs Table
      ```SQL
      CREATE TABLE DeviationLogs (
        switch VARCHAR(255),
        port INT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        message VARCHAR(255),
        PRIMARY KEY (timestamp, switch, port)
      );
      ```
  
 2. Fill in the neccesary fields flagged with ***** in the code.
    - Note: To get the ORG_ID use the org.py tool included. Instructions below.

**Dependencies**

- Ensure Python 3.x is installed on your system.
- Install necessary Python packages by running:
```
  pip install requests pymysql
```

 **Usage**
 
- To run the tool, use the following command in the terminal:
```
python portdata.py
```
- For updating the summary table, use:
```
python [script_name].py update_summary
```

**ORG.PY USAGE**

This is a simple program to retrieve the organization ID, simply enter your API key and it will return the organizations you are apart of in the terminal.
- To run the tool, use the following command in the terminal:
```
python org.py
```

**AUTOMATIC UPDATING**
To make the code automatically update on a specific time interval Windows Task Scheduler is the most efficient way.

- Steps to set up main:
    - Open Windows Task Scheduler
    - Click "Create Basic Task"
    - Give the task a name (description is optional). Click "Next".
    - Choose the "Daily" option. Click "Next".
    - Set it to start at a specific time, and recur every 1 day. Click "Next".
    - Select "Start a Program". Click "Next".
    - Choose browse and naviagte to where your "python.exe" is saved.
    - In the "Add arguments" box enter the path to your script, e.g.: 'C:\path\to\your\script.py'. Click "Next".
    - Check "Open the Properties dialog for this task when I click Finish".
    - Click "Finish".
    - When the Properties dialog opens click the "Triggers" tab.
    - Double click the Trigger.
    - Check the box "Repeat task every:".
    - Choose "30 minutes" (or desired interval).
    - Choose "Indefinitely" from the "for a duration of:" dropdown.
    - Click "Ok" on both windows.
 
- Steps to set up update_daily_summary:
    - Repeat the steps in "Create Basic Task" for your update_daily_summary function. Set it to trigger daily at a specific time, and in the "Add Arguments" section, include the necessary argument to trigger the update_daily_summary function (like C:\path\to\your\script.py update_summary).
 
- Test Your Tasks
    - After setting up, it's important to test both tasks to ensure they're running as expected. You can right-click each task in the Task Scheduler and select "Run" to test them immediately.
 
This setup should allow your main script to run every 30 minutes and the update_daily_summary function to execute once every 24 hours.
