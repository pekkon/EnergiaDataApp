import os, requests
import pandas as pd
import streamlit as st
import json
import datetime as dt


"""
Reads json-file given by Fingrid's open data API and converts it to list of timestamps and values
"""

def get_data_from_fg_api_with_start_end(variableid, start, end):
    headers = {'x-api-key': os.environ['FGAPIKEY']}
    start_str = start.strftime("%Y-%m-%dT") + "00:00:00"
    end_str = end.strftime("%Y-%m-%dT") + "23:59:00"
    res = requests.api.get(f'https://data.fingrid.fi/api/datasets/{variableid}/data?startTime={start_str}Z&'
                           f'endTime={end_str}Z&format=json&oneRowPerTimePeriod=true&pageSize=20000&'
                           f'locale=fi&sortBy=startTime&sortOrder=asc',
                           headers=headers)
    res_decoded = res.content.decode('utf-8')
    response = json.loads(res_decoded)
    df = pd.DataFrame(response['data'])
    num_of_pages = response['pagination']['lastPage']
    if num_of_pages > 1:
        for page in range(2, num_of_pages + 1):
            next_res = requests.api.get(
                f'https://data.fingrid.fi/api/datasets/{variableid}/data?startTime={start_str}Z&'
                f'endTime={end_str}Z&format=json&oneRowPerTimePeriod=true&pageSize=20000&page={page}&'
                f'locale=fi&sortBy=startTime&sortOrder=asc',
                headers=headers)
            next_res_decoded = next_res.content.decode('utf-8')
            next_df = pd.DataFrame(json.loads(next_res_decoded)['data'])
            df = pd.concat([df, next_df])
    df.columns = ['Aikaleima', 'End', 'Value']
    df['Aikaleima'] = pd.to_datetime(df['Aikaleima']).dt.tz_convert('Europe/Helsinki')
    df.set_index('Aikaleima', inplace=True)
    df.drop('End', inplace=True, axis=1)
    return df
