import os, requests
import pandas as pd
import streamlit as st


"""
Reads json-file given by Fingrid's open data API and converts it to list of timestamps and values
"""



def get_data_from_FG_API_with_start_end(variableid, start, end):
    headers = {'x-api-key': os.environ['FGAPIKEY']}
    start_str = start.strftime("%Y-%m-%dT") + "00:00:00+03:00"
    end_str = end.strftime("%Y-%m-%dT") + "23:59:00+03:00"
    params = {'start_time': start_str, 'end_time': end_str, 'response_timezone': "+03:00"}
    r = requests.get(f'https://api.fingrid.fi/v1/variable/{variableid}/events/json', params=params, headers=headers)
    content = r.content.decode('utf-8')
    df = pd.read_json(content)
    df.columns = ['Value', 'Aikaleima', 'End']
    df['Aikaleima'] = pd.to_datetime(df['Aikaleima'])
    df.set_index('Aikaleima', inplace=True)
    df.drop('End', inplace=True, axis=1)
    return df
