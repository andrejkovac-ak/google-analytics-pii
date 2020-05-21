# Google Analytics PII Detection

Simple python script which detects if your views contains any PII. Results are stored in csv file and uploaded to drive folder.

## Getting Started

1. Open the Google API Console Credentials page.
2. From the project drop-down, choose Create a new project, enter a name for the project, and optionally, edit the provided Project ID. Click Create.
3. On the Credentials page, select Create credentials, then select Service account.
4. Supply the requested information, and click Create.
5. On the page that appears, you can download client secret as a JSON file. Save it in the same directory as python script and name it "client_secret.json"
6. Enable Google Analytics Reporting API and Google Drive API

### Prerequisites

After obtaining client secret, you need to install required libraries.

```
pip install requirements.txt
```

### Setup

To run a script, set Google Analytics views ID, dimensions ID and google drive folder ID.

To find ID of your drive folder, navigate to the folder and copy last part of URL. <https://prnt.sc/sl5aki>

```
VIEWS = [{'view_id': 'VIEW ID HERE',
          'view_name': 'VIEW NAME HERE'},
         {'view_id': 'VIEW ID HERE',
          'view_name': 'VIEW NAME HERE'}]
DIMENSIONS = [{'dim_id': {'name': 'ga:hostname'},
               'dim_name': 'Hostname'},
              {'dim_id': {'name': 'ga:pagePath'},
               'dim_name': 'Page path with params'}]
MAIN_FOLDER = 'YOUR FOLDER ID HERE'
```