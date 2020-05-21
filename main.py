import time
from datetime import datetime

import numpy as np
import pandas as pd
import schedule
from apiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials

GA_SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']
KEY_FILE_LOCATION = 'client_secret.json'

VIEWS = [{'view_id': 'VIEW ID HERE',
          'view_name': 'VIEW NAME HERE'},
         {'view_id': 'VIEW ID HERE',
          'view_name': 'VIEW NAME HERE'}]
DIMENSIONS = [{'dim_id': {'name': 'ga:hostname'},
               'dim_name': 'Hostname'},
              {'dim_id': {'name': 'ga:pagePath'},
               'dim_name': 'Page path with params'}]
MAIN_FOLDER = 'YOUR FOLDER ID HERE'


def initialize_analyticsreporting():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        KEY_FILE_LOCATION, GA_SCOPES)

    # Build the service object.
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    return analytics


def initialize_drive():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        KEY_FILE_LOCATION, DRIVE_SCOPES)

    # Build the service object.
    drive = build('drive', 'v3', credentials=credentials)

    return drive


def get_report(analytics, view_id, dimension, page_token):
    """
    Single request can return only 100,000 rows.
    page_token is used to indicate which results should the request return
    In first iteration, page_token is set to 0
    """
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': view_id,
                    'dateRanges': [{'startDate': '7daysAgo', 'endDate': 'yesterday'}],
                    'metrics': [{'expression': 'ga:pageviews'}],
                    'dimensions': [dimension],
                    'pageToken': page_token,
                    'pageSize': 100000,
                    'samplingLevel': 'LARGE',
                }]
        }
    ).execute()


def handle_request(analytics, view_id, view_name, source_dimension, page_token, dim, val):
    source_dimension_id = source_dimension.get('dim_id')
    source_dimension_name = source_dimension.get('dim_name')

    response = get_report(analytics, view_id, source_dimension_id, page_token)

    for report in response.get('reports', []):
        column_header = report.get('columnHeader', {})
        dimension_headers = column_header.get('dimensions', [])
        metric_headers = column_header.get('metricHeader', {}).get('metricHeaderEntries', [])

        # get "nextPageToken" or set it to None
        page_token = report.get('nextPageToken', None)

        rows_new = report.get('data', {}).get('rows', [])

        # get dimensions&values and append them to lists
        for row in rows_new:
            dimensions = row.get('dimensions', [])
            date_range_values = row.get('metrics', [])

            for header, dimension in zip(dimension_headers, dimensions):
                dim.append(dimension)

            for i, values in enumerate(date_range_values):
                for metricHeader, value in zip(metric_headers, values.get('values')):
                    val.append(int(value))

        print(f'Number of unique pages: {len(dim)}')

    if page_token is not None:
        return handle_request(analytics, view_id, view_name, source_dimension, page_token, dim, val)
    else:
        return source_dimension_name, dim, view_name, val


def handle_dataframe(dim_head, dim, view, val):
    # create empty DataFrame
    df = pd.DataFrame()

    metric = 'Pageviews'

    df[metric] = val
    df[dim_head] = dim
    df = df[[dim_head, metric]]

    """
    1. Sort DataFrame by number of pageviews
    2. Replace ";" character in all Pages, which could cause troubles while exporting to csv
    """

    df = df.sort_values(by=[metric], ascending=False)
    df[dim_head] = df[dim_head].str.replace(r';', '')

    regex_pii = '[^\s@\.\/-]@|(pass(word|wd)?|pwd)=\w+|(tel(ephone)?|phone|mob(ile)?)=\+?\d{2}|address=\w+|(post(' \
                'code|alcode)?|zip(code)?)=\d+ '

    # create a new column "PII" which indicates if PII is present or not
    df['PII'] = np.where(df[dim_head].str.contains(regex_pii), 'YES', 'NO')

    # create a new DataFrame with PII pages only
    df_pii = df[df['PII'] == 'YES']

    report_name = f"PII - {view} - {dim_head}.csv"

    df_pii.to_csv(report_name)

    return report_name


def upload_report(report):
    drive = initialize_drive()
    folder = create_subfolder(drive)
    file_metadata = {'name': report,
                     'parents': [folder],
                     'mimeType': 'application/vnd.google-apps.spreadsheet'}

    media = MediaFileUpload(report, mimetype='text/csv',
                            resumable=True)
    file = drive.files().create(body=file_metadata,
                                media_body=media,
                                fields='id')
    file.execute()


def create_subfolder(drive):
    date = datetime.today().strftime('%d-%m-%y')
    folder_name = '{} - GA PII Reports'.format(date)
    search_query = f"'{MAIN_FOLDER}' in parents"

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [MAIN_FOLDER]
    }
    files_response = drive.files().list(q=search_query,
                                        spaces='drive',
                                        fields='files(id, name)').execute()

    files = files_response.get('files')
    for file in files:
        file_name = file.get('name')
        if file_name == folder_name:
            return file.get('id')

    file = drive.files().create(body=file_metadata,
                                fields='id').execute()
    folder_id = file.get('id')

    return folder_id


def handle_email():
    # TODO: allow sending emails
    pass


def main():
    analytics = initialize_analyticsreporting()

    for view in VIEWS:
        view_id = view.get('view_id')
        view_name = view.get('view_name')

        for source_dimension in DIMENSIONS:
            dim, val = [], []
            dim_head, dim, view_name, val = handle_request(analytics, view_id, view_name, source_dimension, '0',
                                                           dim, val)
            report = handle_dataframe(dim_head, dim, view_name, val)
            upload_report(report)
    # handle_email()


if __name__ == "__main__":
    main()

# schedule.every().monday.at("06:00").do(main)
#
# while True:
#     schedule.run_pending()
#     time.sleep(30)
